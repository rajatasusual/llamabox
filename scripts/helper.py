import gc  # Import garbage collection module

import requests
import numpy as np
import json

from redis import Redis
from redis.commands.search.query import Query

EMBEDDING_SERVER = "http://localhost:8000/embedding"  # Llama-cpp endpoint
REDIS_HOST = "localhost"
REDIS_PORT = 6379

# Redis connection (set decode_responses=False to handle binary data properly)
redis_conn = Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=False)


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
        
def redis_search(query_text):
    """Search for documents in Redis using the query text."""
    try: 
        # Compute embedding from the query text
        response = requests.post(EMBEDDING_SERVER, json={"content": [query_text]})
        if response.status_code != 200:
            return jsonify({"error": "Failed to compute embedding"}), 500

        query_embedding = np.array(response.json()[0]['embedding'], dtype=np.float32).tobytes()

        # KNN Search Query using your "vector_idx"
        search_query = (
            Query("*=>[KNN 5 @embedding $vec AS score]")  # Find 5 nearest neighbors
            .sort_by("score", asc=False)  # Sort by similarity score
            .return_fields("content", "score")  # Retrieve content and score
            .paging(0, 5)  # Limit results
            .dialect(2)  # Use dialect 2 for better query parsing
        )

        # Perform the search in Redis
        results = redis_conn.ft("vector_idx").search(search_query, query_params={"vec": query_embedding})
        
        # Format the results
        documents = []
        for doc in results.docs:
            
            doc_id = doc.id
            print(f"Document ID: {doc_id}, Score: {doc.score}")
            
            # get document from doc.id
            doc_data = redis_conn.hgetall(f"{doc_id}")
            if doc_data:
                decoded_doc = decode_redis_data(doc_data)
                documents.append({
                    "id": doc_id,
                    "score": doc.score,
                    "title": decoded_doc["title"],
                    "url": decoded_doc["url"],
                    "date": decoded_doc["date"],
                    "content": decoded_doc["snippet"],
                    "relations": json.loads(decoded_doc.get("relations", "{}")),
                    "named_entities": json.loads(decoded_doc.get("named_entities", "{}"))
                })

        return documents
    except Exception as e:
        raise Exception(f"Failed to perform Redis search: {e}")
    finally:
        redis_conn.close()
        print("Redis connection closed.")
        gc.collect()