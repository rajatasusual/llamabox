import numpy as np  # Import numpy to handle the conversion
from redis import Redis
from redis.commands.search.field import TextField, TagField, VectorField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from rq import Queue

from neo4j import GraphDatabase

import requests
import uuid
import json
import os

# Configuration
EMBEDDING_SERVER = "http://localhost:8000/embedding"  # Llama-cpp endpoint
REDIS_HOST = "localhost"
REDIS_PORT = 6379
VECTOR_STORE = "vectors.json"  # Local storage for embeddings (replace with DB if needed)
ENTITY_STORE = "entities.json"  # Local storage for entities (replace with DB if needed)

# Redis connection (set decode_responses=False to handle binary data properly)
redis_conn = Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=False)

schema = (
    TextField("content"),
    TagField("genre"),
    VectorField("embedding", "HNSW", {
        "TYPE": "FLOAT32",
        "DIM": 384,
        "DISTANCE_METRIC": "L2"
    })
)

try:
    redis_conn.ft("vector_idx").create_index(
        schema,
        definition=IndexDefinition(
            prefix=["doc:"], index_type=IndexType.HASH
        )
    )
except Exception as e:
    if "Index already exists" not in str(e):
        print("Error creating index:", e)

def decode_redis_data(doc_data):
    """Decode Redis data, handling binary and UTF-8 strings."""
    decoded_data = {}
    for k, v in doc_data.items():
        key_decoded = k.decode("utf-8") if isinstance(k, bytes) else k
        try:
            value_decoded = v.decode("utf-8") if isinstance(v, bytes) else v
        except UnicodeDecodeError:
            value_decoded = v  # Keep as bytes if it fails to decode
        decoded_data[key_decoded] = value_decoded
    return decoded_data

def store_document_in_redis(doc_id, item, embedding_bytes):
    """Store document and embedding in Redis."""
    mapping = {k: str(v) for k, v in item.items() if k != "embedding"}
    redis_conn.hset(f"doc:{doc_id}", mapping=mapping)
    redis_conn.hset(f"doc:{doc_id}", "embedding", embedding_bytes)
    print(f"Added document with UUID: {doc_id}")

def save_to_local_file(file_path, data):
    """Save data to a local JSON file."""
    with open(file_path, "a") as f:
        json.dump(data, f)
        f.write("\n")

def embed_snippet(data, timestamp, test=False):
    """Processes the snippet data: gets embeddings, stores them, and enqueues an extraction task."""
    try:
        snippets = [item["snippet"] for item in data if "snippet" in item and item["snippet"].strip()]

        if not snippets:
            print(f"[{timestamp}] No valid snippets found. Skipping processing.")
            return

        response = requests.post(EMBEDDING_SERVER, json={"content": snippets})

        if response.status_code == 200:
            embeddings = [item['embedding'][0] for item in response.json()]
            if len(embeddings) != len(snippets):
                print(f"[{timestamp}] Warning: Mismatch between snippets and embeddings count!")
                return

            processed_data = [
                {
                    **{k: item[k] for k in ['date', 'title', 'url'] if k in item},
                    "snippet": item["snippet"],
                    "embedding": embedding
                }
                for item, embedding in zip(data, embeddings)
            ]

            for item in processed_data:
                doc_id = str(uuid.uuid4())
                item["id"] = doc_id
                embedding_bytes = np.array(item["embedding"], dtype=np.float32).tobytes()
                store_document_in_redis(doc_id, item, embedding_bytes)

                if test:
                    return doc_id
                else:
                    queue = Queue("snippet_queue", connection=redis_conn)
                    queue.enqueue(extract_snippet, {"doc_id": doc_id})

            if not test:
                # Save the processed data to a local file
                save_to_local_file(VECTOR_STORE, {"timestamp": timestamp, "data": processed_data})
            print(f"[{timestamp}] Successfully processed {len(snippets)} snippets.")

        else:
            print(f"[{timestamp}] Embedding server error: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"[{timestamp}] Error processing snippet: {e}")
    finally:
        redis_conn.close()
        print("Redis connection closed.")

def extract_snippet(task_payload, test=False):
    """Processes a task from the queue by extracting information."""
    try:
        doc_id = task_payload.get("doc_id")

        if not doc_id:
            print("Invalid task payload, missing 'doc_id'")
            return

        doc_data = redis_conn.hgetall(f"doc:{doc_id}")
        doc_data = decode_redis_data(doc_data)
        
        if not doc_data or "snippet" not in doc_data:
            print(f"Document {doc_id} not found or missing snippet.")
            return
        
        snippet = doc_data["snippet"]

        from information_extractor.main import extract_information

        relations, named_entities = extract_information(snippet)

        print(f"Extracted relations: {relations}")
        print(f"Named entities: {named_entities}")

        relations_dict = {f"{s}||{r}||{o}": float(c) for (s, r, o), c in relations.items()}
        named_entities_list = {k: list(v) if isinstance(v, set) else v for k, v in named_entities.items()}
        
        redis_conn.hset(f"doc:{doc_id}", mapping={
            "relations": json.dumps(relations_dict),
            "named_entities": json.dumps(named_entities_list)
        })

        if not test:
            save_to_local_file(ENTITY_STORE, {"doc_id": doc_id, "relations": relations_dict, "named_entities": named_entities_list})

        print(f"Extraction completed for document {doc_id}: {relations}")
        
        if test:
            return doc_id
        else:
            # Enqueue the next task to load the snippet into Neo4j
            queue = Queue("snippet_queue", connection=redis_conn)
            queue.enqueue(load_snippet, {"doc_id": doc_id})
    
    except Exception as e:
        print(f"Error extracting information on line {e.__traceback__.tb_lineno}: {e}")
    finally:
        redis_conn.close()
        print("Redis connection closed.")

def load_snippet(task_payload, test=False):
    """Loads a snippet into Neo4j by retrieving entities and relations from Redis, then inserting them into the graph database."""
    try:
        doc_id = task_payload.get("doc_id")
        if not doc_id:
            print("Invalid task payload, missing 'doc_id'")
            return

        doc_data = redis_conn.hgetall(f"doc:{doc_id}")
        doc_data = decode_redis_data(doc_data)

        named_entities_str = doc_data.get("named_entities")
        relations_str = doc_data.get("relations")
        if not named_entities_str or not relations_str:
            print(f"Document {doc_id} is missing named entities or relations.")
            return

        named_entities = json.loads(named_entities_str)
        relations = json.loads(relations_str)

        uri = "bolt://localhost:7687"
        driver = GraphDatabase.driver(uri, auth=("neo4j", "password"))

        def add_entities_and_relations(tx, named_entities, relations):
            for entity_type, texts in named_entities.items():
                for text in texts:
                    tx.run(
                        """
                        MERGE (e:Entity {text: $text})
                        ON CREATE SET e.type = $entity_type
                        """,
                        text=text,
                        entity_type=entity_type
                    )

            for key, confidence in relations.items():
                parts = key.split("||")
                if len(parts) != 3:
                    print(f"Skipping invalid relation key: {key}")
                    continue

                subject, relation, object_ = parts
                clean_relation = relation.split(":", 1)[-1] if ":" in relation else relation

                tx.run(
                    """
                    MATCH (s:Entity {text: $subject})
                    MATCH (o:Entity {text: $object})
                    MERGE (s)-[r:RELATES {relation: $clean_relation}]->(o)
                    SET r.strength = $confidence
                    """,
                    subject=subject,
                    object=object_,
                    clean_relation=clean_relation,
                    confidence=confidence
                )

        with driver.session() as session:
            try:
                session.execute_write(add_entities_and_relations, named_entities, relations)        
                print(f"Loaded snippet {doc_id} into Neo4j successfully.")
            except Exception as e:
                print(f"Error executing Neo4j transaction: {e}")
                if test:
                    # throw an exception to indicate failure
                    raise Exception(f"Failed Neo4j Transaction for doc ID: {doc_id}")
            finally:
                session.close()
                driver.close()

    except Exception as e:
        print(f"Error loading snippet into Neo4j: {e}")
