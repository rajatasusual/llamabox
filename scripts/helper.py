import gc  # Import garbage collection module

import requests
import numpy as np
import json

from redis import Redis
from redis.commands.search.query import Query
from neo4j import GraphDatabase

EMBEDDING_SERVER = "http://localhost:8000/embedding"  # Llama-cpp endpoint
REDIS_HOST = "localhost"
REDIS_PORT = 6379

# Redis connection (set decode_responses=False to handle binary data properly)
redis_conn = Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=False)

# Neo4j connection
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password"
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

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
        
def redis_search(query_text, k=5):
    """Search for documents in Redis using the query text."""
    try: 
        # Compute embedding from the query text
        response = requests.post(EMBEDDING_SERVER, json={"content": [query_text]})
        if response.status_code != 200:
            return jsonify({"error": "Failed to compute embedding"}), 500

        query_embedding = np.array(response.json()[0]['embedding'], dtype=np.float32).tobytes()

        # KNN Search Query using your "vector_idx"
        search_query = (
            Query(f"*=>[KNN {k} @embedding $vec AS score]")  # Find 5 nearest neighbors
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
        gc.collect()

def fetch_neo4j_data(doc_ids):
    """
    Retrieve document metadata, named entities, and all relationships (both incoming and outgoing)
    from Neo4j for a set of document IDs.
    
    Returns a dictionary where each key is a document ID and its value contains:
      - metadata: title, url, date of the document,
      - entities: a list of tuples (entity text, entity type),
      - relations: a list of dictionaries with details about each relationship.
    """
    query = """
        MATCH (d:Document)-[:MENTIONS]->(e)
        WHERE d.doc_id IN $doc_ids
        OPTIONAL MATCH (e)-[r]-(other)
        RETURN d.doc_id AS doc_id, d.title AS title, d.url AS url, d.date AS date,
               e.text AS entity, e.type AS entity_type,
               TYPE(r) AS relation, other.text AS related_entity, r.confidence AS confidence
    """
    
    with driver.session() as session:
        result = session.run(query, doc_ids=doc_ids)
        entity_relations = {}
        for record in result:
            doc_id = record["doc_id"]
            # Initialize doc entry with metadata if not already present
            if doc_id not in entity_relations:
                entity_relations[doc_id] = {
                    "metadata": {
                        "title": record["title"],
                        "url": record["url"],
                        "date": record["date"]
                    },
                    "entities": set(),
                    "relations": []
                }
            # Add entity info
            entity = (record["entity"], record["entity_type"])
            entity_relations[doc_id]["entities"].add(entity)
            # Add relationship info if available
            if record["relation"]:
                entity_relations[doc_id]["relations"].append({
                    "subject": record["entity"],
                    "relation": record["relation"],
                    "object": record["related_entity"],
                    "confidence": record["confidence"]
                })
        # Convert entity sets to lists for JSON serialization
        for doc_id in entity_relations:
            entity_relations[doc_id]["entities"] = list(entity_relations[doc_id]["entities"])
        return entity_relations


def context_search(query_text, k=5):
    """
    Fetches relevant documents from Redis and enriches them with Neo4j insights.
    Merges entities, relations, and document metadata from Neo4j.
    """
    top_docs = redis_search(query_text, k)

    # Extract raw doc IDs (strip "doc:" prefix)
    doc_id_map = {doc["id"].split(":", 1)[1]: doc for doc in top_docs}
    doc_ids = list(doc_id_map.keys())

    # Fetch Neo4j data for all doc_ids
    neo4j_data = fetch_neo4j_data(doc_ids)

    # Merge Neo4j insights with Redis data
    for raw_doc_id, doc in doc_id_map.items():
        neo_data = neo4j_data.get(raw_doc_id, {})
        metadata = neo_data.get("metadata", {})

        # Merge metadata from Neo4j (prefer Redis unless Neo4j has newer info)
        doc["neo4j_title"] = metadata.get("title", "")
        doc["neo4j_url"] = metadata.get("url", "")
        doc["neo4j_date"] = metadata.get("date", "")

        # Add Neo4j entities and relations
        doc["entities"] = neo_data.get("entities", [])
        doc["neo4j_relations"] = neo_data.get("relations", [])

    return list(doc_id_map.values())
