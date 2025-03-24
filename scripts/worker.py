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

def embed_snippet(data, timestamp):
    """Processes the snippet data: gets embeddings, stores them, and enqueues an extraction task."""
    try:
        # Extract snippets from the input JSON array
        snippets = [item["snippet"] for item in data if "snippet" in item and item["snippet"].strip()]

        if not snippets:
            print(f"[{timestamp}] No valid snippets found. Skipping processing.")
            return

        # Request embeddings from Llama-cpp server
        response = requests.post(EMBEDDING_SERVER, json={"content": snippets})

        if response.status_code == 200:
            # Assuming response.json() returns a list of dicts with key 'embedding'
            embeddings = [item['embedding'][0] for item in response.json()]
            if len(embeddings) != len(snippets):
                print(f"[{timestamp}] Warning: Mismatch between snippets and embeddings count!")
                return

            # Process and store embeddings along with metadata
            processed_data = [
                {
                    **{k: item[k] for k in ['date', 'title', 'url'] if k in item},
                    "snippet": item["snippet"],
                    "embedding": embedding
                }
                for item, embedding in zip(data, embeddings)
            ]

            for item in processed_data:
                # Generate a unique ID for each document
                doc_id = str(uuid.uuid4())
                item["id"] = doc_id

                # Convert the embedding (a list) into bytes
                embedding_bytes = np.array(item["embedding"], dtype=np.float32).tobytes()

                # Remove the embedding from the mapping since we'll set it separately
                mapping = {k: v for k, v in item.items() if k != "embedding"}
                # Store the rest of the fields as strings
                mapping = {k: str(v) for k, v in mapping.items()}

                # Store the document in Redis
                redis_conn.hset(f"doc:{doc_id}", mapping=mapping)
                # Store the embedding bytes
                redis_conn.hset(f"doc:{doc_id}", "embedding", embedding_bytes)
                print(f"Added document with UUID: {doc_id}")

                # Enqueue extraction task **within snippet_queue**
                queue = Queue("snippet_queue", connection=redis_conn)
                queue.enqueue(extract_snippet, {"doc_id": doc_id})

            # Optionally save to a local JSON file (for backup or audit)
            with open(VECTOR_STORE, "a") as f:
                json.dump({"timestamp": timestamp, "data": processed_data}, f)
                f.write("\n")

            print(f"[{timestamp}] Successfully processed {len(snippets)} snippets.")

        else:
            print(f"[{timestamp}] Embedding server error: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"[{timestamp}] Error processing snippet: {e}")
    finally:
        # Close Redis connection
        redis_conn.close()
        print("Redis connection closed.")


# Worker function to process tasks from the queue
def extract_snippet(task_payload):
    
    """Processes a task from the queue by extracting information."""
    try:
        # Parse the task payload
        doc_id = task_payload.get("doc_id")

        if not doc_id:
            print("Invalid task payload, missing 'doc_id'")
            return

        # Retrieve the snippet and metadata from Redis
        doc_data = redis_conn.hgetall(f"doc:{doc_id}")

        # Decode only if the value is a valid UTF-8 string, leave binary data as is
        decoded_data = {}
        for k, v in doc_data.items():
            key_decoded = k.decode("utf-8") if isinstance(k, bytes) else k
            try:
                value_decoded = v.decode("utf-8") if isinstance(v, bytes) else v
            except UnicodeDecodeError:
                value_decoded = v  # Keep as bytes if it fails to decode
            
            decoded_data[key_decoded] = value_decoded

        doc_data = decoded_data
        
        if not doc_data or "snippet" not in doc_data:
            print(f"Document {doc_id} not found or missing snippet.")
            return
        
        snippet = doc_data["snippet"]

        # Call extract_information
        from information_extractor.main import extract_information

        relations, named_entities = extract_information(snippet)

        # print or log the extracted information
        print(f"Extracted relations: {relations}")
        print(f"Named entities: {named_entities}")

        # Convert relations to a dictionary with keys formatted as "subject||relation||object"
        # and values as confidence scores
        relations_dict = {f"{s}||{r}||{o}": float(c) for (s, r, o), c in relations.items()}
        named_entities_list = {k: list(v) if isinstance(v, set) else v for k, v in named_entities.items()}
        
        # Store extracted information back in Redis
        redis_conn.hset(f"doc:{doc_id}", mapping={
            "relations": json.dumps(relations_dict),
            "named_entities": json.dumps(named_entities_list)
        })

        # Optionally save to a local JSON file (for backup or audit)
        with open(ENTITY_STORE, "a") as f:
            json.dump({"doc_id": doc_id, "relations": relations_dict, "named_entities": named_entities_list}, f)
            f.write("\n")

        # Print or log the extracted information
        print(f"Extraction completed for document {doc_id}: {relations}")
        
        queue = Queue("snippet_queue", connection=redis_conn)
        queue.enqueue(load_snippet, {"doc_id": doc_id})
    
    except Exception as e:
        print(f"Error extracting information on line {e.__traceback__.tb_lineno}: {e}")
    finally:
        # close redis connection
        redis_conn.close()
        print("Redis connection closed.")


# Worker function to load the snippet into Neo4j
def load_snippet(task_payload):
    """
    Loads a snippet into Neo4j by retrieving entities and relations from Redis,
    then inserting them into the graph database.
    """
    try:
        doc_id = task_payload.get("doc_id")
        if not doc_id:
            print("Invalid task payload, missing 'doc_id'")
            return

        # Retrieve the snippet data from Redis
        doc_data = redis_conn.hgetall(f"doc:{doc_id}")

        # Decode only if the value is a valid UTF-8 string; leave binary data as is.
        decoded_data = {}
        for k, v in doc_data.items():
            key_decoded = k.decode("utf-8") if isinstance(k, bytes) else k
            try:
                value_decoded = v.decode("utf-8") if isinstance(v, bytes) else v
            except UnicodeDecodeError:
                value_decoded = v  # keep as bytes if decoding fails
            decoded_data[key_decoded] = value_decoded
        doc_data = decoded_data

        # Make sure the required fields are available
        named_entities_str = doc_data.get("named_entities")
        relations_str = doc_data.get("relations")
        if not named_entities_str or not relations_str:
            print(f"Document {doc_id} is missing named entities or relations.")
            return

        # Convert JSON strings to Python objects
        named_entities = json.loads(named_entities_str)
        relations = json.loads(relations_str)

        # Connect to Neo4j
        uri = "bolt://localhost:7687"
        driver = GraphDatabase.driver(uri, auth=("neo4j", "password"))

        def add_entities_and_relations(tx, named_entities, relations):
            # Create nodes for each entity.
            # 'named_entities' is a dict: entity_type -> list of entity texts.
            for entity_type, texts in named_entities.items():
                for text in texts:
                    # Merge an Entity node with properties text and type.
                    tx.run(
                        """
                        MERGE (e:Entity {text: $text})
                        ON CREATE SET e.type = $entity_type
                        """,
                        text=text,
                        entity_type=entity_type
                    )

            # Create relationships between entities.
            # 'relations' is a dict with keys in the format "subject||relation||object"
            # and values representing the confidence score.
            for key, confidence in relations.items():
                parts = key.split("||")
                if len(parts) != 3:
                    print(f"Skipping invalid relation key: {key}")
                    continue

                subject, relation, object_ = parts
                # Clean up the relationship string: remove any prefix like "per:" or "org:".
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
            session.write_transaction(add_entities_and_relations, named_entities, relations)

        driver.close()
        print(f"Loaded snippet {doc_id} into Neo4j successfully.")

    except Exception as e:
        print(f"Error loading snippet into Neo4j: {e}")
