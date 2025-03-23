import numpy as np  # Import numpy to handle the conversion
from redis import Redis
from redis.commands.search.query import Query
from redis.commands.search.field import TextField, TagField, VectorField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
import requests
import uuid
import json
import os
from rq import Queue

# Configuration
EMBEDDING_SERVER = "http://localhost:8000/embedding"  # Llama-cpp endpoint
REDIS_HOST = "localhost"
REDIS_PORT = 6379
VECTOR_STORE = "vectors.json"  # Local storage for embeddings (replace with DB if needed)

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
    print("Index 'vector_idx' already exists or error encountered:", e)

def process_snippet(data, timestamp):
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

        relations, doc, resolved_text, named_entities = extract_information(snippet)

        # Store extracted information back in Redis
        redis_conn.hset(f"doc:{doc_id}", "relations", json.dumps(relations))
        redis_conn.hset(f"doc:{doc_id}", "resolved_text", resolved_text)
        redis_conn.hset(f"doc:{doc_id}", "named_entities", json.dumps(named_entities))

        print(f"Extraction completed for document {doc_id}: {relations}")

    except Exception as e:
        print(f"Error extracting information: {e}")
    finally:
        # close redis connection
        redis_conn.close()
        print("Redis connection closed.")

