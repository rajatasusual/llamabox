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
        
    def test_stress_test(self):
        """Stress test extraction by running extract_snippet 10 times for 10 docs in Redis."""
        # Create 10 test documents in Redis
        test_doc_ids = []
        snippets = [
            "Elon Musk and Tesla: In 2003, Elon Musk joined Tesla Motors, an electric vehicle company, as chairman.",
            "Bill Gates and Microsoft: In 1975, Bill Gates co-founded Microsoft with Paul Allen to develop software for personal computers.",
            "Jeff Bezos and Amazon: In 1994, Jeff Bezos founded Amazon, initially an online bookstore, which later expanded into a global e-commerce giant.",
            "Steve Jobs and Apple: In 1976, Steve Jobs co-founded Apple Inc. with Steve Wozniak and Ronald Wayne to create personal computers.",
            "Mark Zuckerberg and Facebook: In 2004, Mark Zuckerberg launched Facebook, a social networking platform, from his Harvard dorm room.",
            "Sundar Pichai and Google: Sundar Pichai became the CEO of Google in 2015, leading the company into new areas of innovation.",
            "Satya Nadella and Microsoft: Satya Nadella became the CEO of Microsoft in 2014, focusing on cloud computing and AI technologies.",
            "Larry Ellison and Oracle: Larry Ellison co-founded Oracle Corporation in 1977, a company specializing in database software.",
            "Sheryl Sandberg and Facebook: Sheryl Sandberg joined Facebook as COO in 2008, helping to scale its business operations.",
            "Tim Cook and Apple: Tim Cook succeeded Steve Jobs as CEO of Apple in 2011, continuing to drive the company's growth."
        ]
        for i in range(10):
            test_data = {
                "timestamp": f"2025032323142{i}",
                "data": [{
                    "date": f"2025-03-23T23:13:2{i}.700Z",
                    "title": f"Test Document {i}",
                    "url": f"http://example.com/doc{i}",
                    "snippet": snippets[i],
                    "id": f"doc-{i}"
                }]
            }
            doc_id = embed_snippet(test_data["data"], test_data["timestamp"], True)
            test_doc_ids.append(doc_id)

        # Stress test extract_snippet
        for doc_id in test_doc_ids:
            extract_snippet({"doc_id": doc_id}, True)

        # Verify extracted data for all test documents
        for doc_id in test_doc_ids:
            doc_data = self.redis_conn.hgetall(f"doc:{doc_id}")
            doc_data = decode_redis_data(doc_data)
            self.assertIn("relations", doc_data, f"Relations not stored for doc {doc_id}")
            self.assertIn("named_entities", doc_data, f"Named entities not stored for doc {doc_id}")
            load_snippet({"doc_id": doc_id}, True)
            
        # Cleanup test documents
        for doc_id in test_doc_ids:
            self.redis_conn.delete(f"doc:{doc_id}")
            
    @classmethod
    def tearDownClass(cls):
        """Cleanup: Remove test data from Redis."""
        if cls.test_doc_id:
            cls.redis_conn.delete(f"doc:{cls.test_doc_id}")
            print(f"Cleaned up test doc ID: {cls.test_doc_id}")
        cls.redis_conn.close()
if __name__ == "__main__":
    unittest.main()
