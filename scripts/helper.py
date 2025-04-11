import gc  # Import garbage collection module

import requests
import numpy as np
import json

from redis import Redis
from redis.commands.search.query import Query
from neo4j import GraphDatabase

EMBEDDING_SERVER = "http://localhost:8000/embedding"  # Llama-cpp endpoint
RERANK_SERVER = "http://localhost:8008/rerank"
LLAMA_SERVER = "http://localhost:8080/completion"
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
            Query(f"*=>[KNN {k} @embedding $vec AS score]")  # Find k nearest neighbors
            .sort_by("score", asc=False)  # Sort by similarity score
            .return_fields("score")  # Retrieve content and score
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

def neo4j_enrich(doc_ids):
    """
    Retrieve document metadata, named entities, and all relationships (both incoming and outgoing)
    from Neo4j for a set of document IDs.
    
    Returns a dictionary where each key is a document ID and its value contains:
      - metadata: title, url, date of the document,
      - entities: a list of tuples (entity text, entity type),
      - relations: a list of dictionaries with details about each relationship.
      
    Relationships are deduplicated based on the tuple (subject, relation, object) while keeping
    only the highest confidence value for duplicate relationships.
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
            # Initialize the document's entry if not already present.
            if doc_id not in entity_relations:
                entity_relations[doc_id] = {
                    "metadata": {
                        "title": record["title"],
                        "url": record["url"],
                        "date": record["date"]
                    },
                    # Use a set to deduplicate entities by name and type.
                    "entities": set(),
                    # Use a dict to deduplicate relationships based on (subject, relation, object).
                    "relations": {}
                }
            # Add entity info to the set.
            entity = (record["entity"], record["entity_type"])
            entity_relations[doc_id]["entities"].add(entity)
            
            # Process relationship info if available.
            if record["relation"]:
                key = (record["entity"], record["relation"], record["related_entity"])
                confidence = record["confidence"]
                # If the same relationship exists, keep the one with the higher confidence.
                if key in entity_relations[doc_id]["relations"]:
                    if confidence is not None and confidence > entity_relations[doc_id]["relations"][key]["confidence"]:
                        entity_relations[doc_id]["relations"][key]["confidence"] = confidence
                else:
                    entity_relations[doc_id]["relations"][key] = {
                        "subject": record["entity"],
                        "relation": record["relation"],
                        "object": record["related_entity"] if record["relation"] != "MENTIONS" and record["related_entity"] else doc_id,
                        "confidence": confidence if confidence is not None and record["relation"] != "MENTIONS" else 1.0
                    }
                    
        # Convert sets and dictionaries to lists for JSON serialization.
        for doc_id in entity_relations:
            entity_relations[doc_id]["entities"] = list(entity_relations[doc_id]["entities"])
            entity_relations[doc_id]["relations"] = list(entity_relations[doc_id]["relations"].values())
            
        return entity_relations

def rerank_docs(query_text, redis_docs, top_k=3):
    """
    Sends document content to the local reranker service and returns the top-k most relevant documents.

    Args:
        query_text (str): The query for reranking.
        redis_docs (list): List of documents retrieved from Redis (with 'content' field).
        top_k (int): Number of top documents to return after reranking.

    Returns:
        List of top-k documents (with rerank scores added).
    """
    # Prepare request payload
    doc_texts = [doc.get("content", "") for doc in redis_docs]

    payload = {
        "query": query_text,
        "documents": doc_texts
    }

    try:
        response = requests.post(RERANK_SERVER, json=payload)
        response.raise_for_status()
        rerank_results = response.json().get("results", [])

        # Attach relevance scores to the corresponding documents
        for result in rerank_results:
            idx = result["index"]
            score = result["relevance_score"]
            redis_docs[idx]["rerank_score"] = score

        # Sort by relevance score (descending) and return top_k
        top_reranked = sorted(redis_docs, key=lambda d: d.get("rerank_score", float("-inf")), reverse=True)
        return top_reranked[:top_k]

    except requests.RequestException as e:
        print(f"Error during reranking: {e}")
        return redis_docs[:top_k]  # Fallback: return top-k from original

def neo4j_search(query_text, k=5):
    top_docs = redis_search(query_text, k)
    top_docs = rerank_docs(query_text, top_docs)

    # Extract raw doc IDs (strip "doc:" prefix)
    doc_id_map = {doc["id"].split(":", 1)[1]: doc for doc in top_docs}
    doc_ids = list(doc_id_map.keys())

    # Fetch Neo4j data for all doc_ids
    return neo4j_enrich(doc_ids)

def extract_facts_and_entities(docs, confidence_threshold=0.8, max_facts=5):
    facts = []
    entities = {}
    fact_id = 1

    for doc in docs:
        # Extract named entities
        for ent_type, ent_values in doc.get("named_entities", {}).items():
            if ent_type not in entities:
                entities[ent_type] = set()
            entities[ent_type].update(ent_values)

        # Extract high-confidence facts from relations
        for rel in doc.get("neo4j_relations", []):
            subj = rel.get("subject")
            rel_type = rel.get("relation")
            obj = rel.get("object")
            conf = rel.get("confidence")

            if not subj or not rel_type or not obj:
                continue
            if conf is not None and conf < confidence_threshold:
                continue

            # Create readable sentence
            fact_sentence = f"{subj} has relation '{rel_type}' with {obj}."
            if conf is not None:
                fact_sentence += f" [confidence: {round(conf, 2)}]"

            facts.append((fact_id, fact_sentence))
            fact_id += 1

    # Sort by confidence (if available)
    def get_conf_score(fact):
        try:
            return float(fact[1].split('[confidence: ')[-1].rstrip(']'))
        except:
            return 0.5

    facts.sort(key=get_conf_score, reverse=True)

    # Deduplicate facts
    seen = set()
    unique_facts = []
    for fid, f in facts:
        if f not in seen:
            seen.add(f)
            unique_facts.append((fid, f))
        if len(unique_facts) >= max_facts:
            break

    # Convert entity sets to sorted lists
    entities = {k: sorted(list(v)) for k, v in entities.items()}

    return unique_facts, entities

def build_prompt(query, facts, entities, docs, include_content=True):
    lines = [
        "You are an expert in generating answer to a question based on shared information. Keep answer short.",
        "Rules:\n1. ONLY use the provided facts and documents.\n2. DO NOT use external or assumed information.\n3. If unsure, reply: 'Not enough information.'\n4. Keep the answer short and direct.",
        "---",
    ]
    if include_content:
        lines.append("\Information:")
        for idx, doc in enumerate(docs, 1):
            lines.append(f"\nDocument {idx}:\n{doc['content']}")

    if facts:
        lines.append("\nFacts:")
        for fact_id, fact in facts:
            lines.append(f"\nFact {fact_id}: {fact}")

    if entities:
        lines.append("\nNamed Entities:")
        for ent_type, ent_values in entities.items():
            lines.append(f"\n{ent_type}: {', '.join(ent_values)}")

    lines.append("\nQuestion:")
    lines.append(query)
    lines.append("\n---")
    lines.append("\nAnswer:")

    return "\n".join(lines)

def call_slm(prompt, endpoint=LLAMA_SERVER):
    payload = {"prompt": prompt}
    response = requests.post(endpoint, json=payload)
    response.raise_for_status()
    return response.json() if response.status_code == 200 else None

def generate_answer(query, docs, include_content=True):
    facts, entities = extract_facts_and_entities(docs)
    prompt = build_prompt(query, facts, entities, docs, include_content=include_content)
    completion = call_slm(prompt)

    return {
        "completion": completion,
        "prompt": prompt,
        "facts_used": facts,
        "named_entities": entities
    }


def context_search(query_text, k=5):
    """
    Fetches relevant documents from Redis and enriches them with Neo4j insights.
    Merges entities, relations, and document metadata from Neo4j.
    """
    neo4j_data = nsearch(query_text)

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
 
    return generate_answer(query_text, doc_id_map.values())
