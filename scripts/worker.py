from redis import Redis
from redis.commands.search.query import Query
from redis.commands.search.field import TextField, TagField, VectorField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
import requests
import uuid 
import json
import os

# Configuration
EMBEDDING_SERVER = "http://localhost:8000/embedding"  # Llama-cpp endpoint
REDIS_HOST = "localhost"
REDIS_PORT = 6379
VECTOR_STORE = "vectors.json"  # Local storage for embeddings (replace with DB if needed)

# Redis connection
redis_conn = Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
schema = (
    TextField("content"),
    TagField("genre"),
    VectorField("embedding", "HNSW", {
        "TYPE": "FLOAT32",
        "DIM": 384,
        "DISTANCE_METRIC":"L2"
    })
)

redis_conn.ft("vector_idx").create_index(
    schema,
    definition=IndexDefinition(
        prefix=["doc:"], index_type=IndexType.HASH
    )
)

def process_snippet(data, timestamp):
    """Processes the snippet data: gets embeddings and stores them."""
    try:
        # Extract snippets from the input JSON array
        snippets = [item["snippet"] for item in data if "snippet" in item and item["snippet"].strip()]
        
        if not snippets:
            print(f"[{timestamp}] No valid snippets found. Skipping processing.")
            return

        # Request embeddings from Llama-cpp server
        response = requests.post(EMBEDDING_SERVER, json={"content": snippets})

        if response.status_code == 200:
            embeddings = [item['embedding'][0] for item in response.json()]
            if len(embeddings) != len(snippets):
                print(f"[{timestamp}] Warning: Mismatch between snippets and embeddings count!")
                return

            # Store embeddings along with metadata
            processed_data = [
                {
                    **{k: item[k] for k in ['date', 'title', 'url'] if k in item},
                    "snippet": item["snippet"],
                    "embedding": embedding
                }
                for item, embedding in zip(data, embeddings)
            ]

            # Store in Redis
            for item in processed_data:
                # Generate a unique ID for each document
                item["id"] = str(uuid.uuid4())
                # Store the item in Redis
                redis_conn.hset(f"doc:{item['id']}", mapping=item)
                # Add to the vector index
                redis_conn.hset(f"doc:{item['id']}", "embedding", bytes(str(item["embedding"]), 'utf-8'))
                print(f"[{item["id"]}] Added document with UUID: {item['id']}")
            # Save to a local JSON file (or replace with database storage)
            with open(VECTOR_STORE, "a") as f:
                json.dump({"timestamp": timestamp, "data": processed_data}, f)
                f.write("\n")

            print(f"[{timestamp}] Successfully processed {len(snippets)} snippets.")

        else:
            print(f"[{timestamp}] Embedding server error: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"[{timestamp}] Error processing snippet: {e}")
