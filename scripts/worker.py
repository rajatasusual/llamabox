import gc  # Import garbage collection module

# Other imports remain the same
from redis import Redis
from redis.commands.search.field import TextField, TagField, VectorField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from rq import Queue, Retry
from neo4j import GraphDatabase
import re
import requests
import uuid
import json
import os
from retry import retry
import numpy as np

from helper import decode_redis_data, store_document_in_redis, save_to_local_file

# Configuration
EMBEDDING_SERVER = "http://localhost:8000/embedding"  # Llama-cpp endpoint
REDIS_HOST = "localhost"
REDIS_PORT = 6379
VECTOR_STORE = "vectors.json"  # Local storage for embeddings (replace with DB if needed)
ENTITY_STORE = "entities.json"  # Local storage for entities (replace with DB if needed)
NEO4J_URI = "bolt://localhost:7687"  # Neo4j URI
neo4j_username = os.getenv("NEO4J_USERNAME", "neo4j")
neo4j_password = os.getenv("NEO4J_PASSWORD", "password")  # Default password, change as needed

redis_conn = Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=False)
driver = GraphDatabase.driver(NEO4J_URI, auth=(neo4j_username, neo4j_password))
        
schema = (
    TextField("content"),
    TagField("genre"),
    VectorField("embedding", "HNSW", {
        "TYPE": "FLOAT32",
        "DIM": 768,
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

def embed_snippet(data, timestamp, test=False):
    """Processes the snippet data: gets embeddings, stores them, and enqueues an extraction task."""
    try:
        snippets = [item["snippet"] for item in data if "snippet" in item and item["snippet"].strip()]

        if not snippets:
            print(f"[{timestamp}] No valid snippets found. Skipping processing.")
            return

        try:
            response = requests.post(EMBEDDING_SERVER, json={"content": snippets})
            response.raise_for_status()  # Raises exception for 4xx/5xx errors
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error: {http_err}")
        except requests.exceptions.ConnectionError as conn_err:
            print(f"Connection error: {conn_err}")

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
                    queue.enqueue(extract_snippet, {"doc_id": doc_id}, retry=Retry(max=3, interval=[10, 30, 60]))  # Retry 3 times with increasing delay

            if not test:
                # Save the processed data to a local file
                save_to_local_file(VECTOR_STORE, {"timestamp": timestamp, "data": processed_data})
            print(f"[{timestamp}] Successfully processed {len(snippets)} snippets.")

        else:
            print(f"[{timestamp}] Embedding server error: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"[{timestamp}] Error processing snippet: {e}")
        if test:
            # throw an exception to indicate failure
            raise Exception(f"Failed to process snippet data: {e}")
    finally:
        redis_conn.close()
        print("Redis connection closed.")
        gc.collect()  # Trigger garbage collection

@retry((requests.exceptions.RequestException, SystemExit), tries=3, delay=5)
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

        # print total keys in relations and named_entities
        print(f"Total relations: {len(relations)}")
        print(f"Total named_entities: {len(named_entities)}")

        relations_dict = {f"{s}||{r}||{o}": float(c) for (s, r, o), c in relations.items()}
        named_entities_list = {k: list(v) if isinstance(v, set) else v for k, v in named_entities.items()}
        
        redis_conn.hset(f"doc:{doc_id}", mapping={
            "relations": json.dumps(relations_dict),
            "named_entities": json.dumps(named_entities_list)
        })

        if not test:
            save_to_local_file(ENTITY_STORE, {"doc_id": doc_id, "relations": relations_dict, "named_entities": named_entities_list})

        print(f"Extraction completed for document {doc_id}")
        
        if test:
            return doc_id
        else:
            # Enqueue the next task to load the snippet into Neo4j
            queue = Queue("snippet_queue", connection=redis_conn)
            queue.enqueue(load_snippet, {"doc_id": doc_id})
    
    except Exception as e:
        print(f"Error extracting information on line {e.__traceback__.tb_lineno}: {e}")
        if test:
            # throw an exception to indicate failure
            raise Exception(f"Failed to extract information for doc ID: {doc_id}")
    finally:
        redis_conn.close()
        print("Redis connection closed.")
        gc.collect()  # Trigger garbage collection

def load_snippet(task_payload, test=False):
    try:
        doc_id = task_payload.get("doc_id")
        if not doc_id:
            print("Invalid task payload, missing 'doc_id'")
            return

        doc_data = redis_conn.hgetall(f"doc:{doc_id}")
        doc_data = decode_redis_data(doc_data)

        named_entities_str = doc_data.get("named_entities")
        title = doc_data.get("title", "")
        url = doc_data.get("url", "")
        date = doc_data.get("date", "")
        relations_str = doc_data.get("relations")
        if not named_entities_str or not relations_str:
            print(f"Document {doc_id} is missing named entities or relations.")
            return

        named_entities = json.loads(named_entities_str)
        relations = json.loads(relations_str)

        def format_relationship_name(rel_name):
            return re.sub(r'[_-]', ' ', rel_name).title()

        def add_entities_and_relations(tx, doc_id, title, url, date, named_entities, relations):
            # Create or update Document node
            tx.run("""
                MERGE (d:Document {doc_id: $doc_id})
                SET d.title = $title, d.url = $url, d.date = $date
            """, doc_id=doc_id, title=title, url=url, date=date)

            entity_label_map = {
                "PERSON": "Person",
                "ORG": "Organization",
                "DATE": "Date",
                "CARDINAL": "Number",
                "GPE": "GeopoliticalEntity",
                "NORP": "Group",
                "FAC": "Facility",
                "LOC": "Location",
                "EVENT": "Event",
                "WORK_OF_ART": "Work",
                "LAW": "Law",
                "PRODUCT": "Product"
            }

            # Add global entities and connect to Document
            for entity_type, texts in named_entities.items():
                label = entity_label_map.get(entity_type, "Entity")
                for text in texts:
                    entity_query = f"""
                    MERGE (e:{label} {{text: $text, type: $entity_type}})
                    """
                    tx.run(entity_query, text=text, entity_type=entity_type)

                    mentions_query = f"""
                    MATCH (d:Document {{doc_id: $doc_id}})
                    MATCH (e:{label} {{text: $text, type: $entity_type}})
                    MERGE (d)-[:MENTIONS]->(e)
                    """
                    tx.run(mentions_query, doc_id=doc_id, text=text, entity_type=entity_type)

            # Add relationships between entities (deduped across docs)
            for key, confidence in relations.items():
                parts = key.split("||")
                if len(parts) != 3:
                    print(f"Skipping invalid relation key: {key}")
                    continue

                subject, relation, object_ = parts
                clean_relation = relation.split(":", 1)[-1] if ":" in relation else relation
                formatted_relation = format_relationship_name(clean_relation)

                relation_query = f"""
                MATCH (s {{text: $subject}})
                MATCH (o {{text: $object}})
                MERGE (s)-[r:`{formatted_relation}`]->(o)
                ON CREATE SET r.confidence = $confidence, r.relation_tuple = $relation_tuple, r.docs = [$doc_id]
                ON MATCH SET r.confidence = (r.confidence + $confidence) / 2,
                              r.docs = CASE WHEN $doc_id IN r.docs THEN r.docs ELSE r.docs + $doc_id END
                """

                tx.run(
                    relation_query,
                    subject=subject,
                    object=object_,
                    confidence=confidence,
                    doc_id=doc_id,
                    relation_tuple=key
                )

        with driver.session() as session:
            session.execute_write(add_entities_and_relations, doc_id, title, url, date, named_entities, relations)
            print(f"Loaded snippet {doc_id} into Neo4j successfully.")

    except Exception as e:
        print(f"Error loading snippet into Neo4j on line {e.__traceback__.tb_lineno}: {e}")
        if test:
            raise Exception(f"Failed to load snippet into Neo4j for doc ID: {doc_id}")
    finally:
        redis_conn.close()
        print("Redis connection closed.")
        driver.close()
        print("Neo4j driver closed.")
        gc.collect()
