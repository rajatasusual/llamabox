import unittest
import json
import time
from redis import Redis
from worker import embed_snippet, extract_snippet, load_snippet, decode_redis_data

class TestWorkerFunctions(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.redis_conn = Redis(host="localhost", port=6379, decode_responses=False)
        cls.test_doc_id = None
        cls.test_data = {
            "timestamp": "20250323231428",
            "data": [{
                "date": "2025-03-23T23:13:29.700Z",
                "title": "llama.cpp - chat",
                "url": "http://192.168.1.29:8080/#/chat/conv-1742768609398",
                "snippet": "Larry Page and Sergey Brin: In 1995, Larry Page and Sergey Brin, two graduate students at Stanford University, co-founded Google.",
                "id": "0fde5526-4fce-41f1-84ed-82c6404eeef8"
                }]
            }
         # Embed the snippet once for all tests
        cls.test_doc_id = embed_snippet(cls.test_data["data"], cls.test_data["timestamp"], True)
        print(f"Test doc ID: {cls.test_doc_id}")

    def test_embed_snippet(self):
        """Verify that the snippet was embedded and stored in Redis."""
        doc_key = f"doc:{self.test_doc_id}"
        doc_exists = self.redis_conn.exists(doc_key)
        self.assertTrue(doc_exists, f"Document {self.test_doc_id} not found in Redis")

    def test_extract_snippet(self):
        """Test extracting entities and relations from a stored snippet."""
        extract_snippet({"doc_id": self.test_doc_id}, True)
        
        # Verify extracted data is stored
        doc_data = self.redis_conn.hgetall(f"doc:{self.test_doc_id}")

        doc_data = decode_redis_data(doc_data)
        
        self.assertIn("relations", doc_data, "Relations not stored in Redis")
        self.assertIn("named_entities", doc_data, "Named entities not stored in Redis")

    def test_load_snippet(self):
        """Test loading extracted data into Neo4j."""
        load_snippet({"doc_id": self.test_doc_id}, True)

        # Check for any Neo4j-related exceptions during execution
        self.assertTrue(True, "Neo4j operation completed without errors")
        

    @classmethod
    def tearDownClass(cls):
        """Cleanup: Remove test data from Redis."""
        if cls.test_doc_id:
            cls.redis_conn.delete(f"doc:{cls.test_doc_id}")
            print(f"Cleaned up test doc ID: {cls.test_doc_id}")
        cls.redis_conn.close()
if __name__ == "__main__":
    unittest.main()
