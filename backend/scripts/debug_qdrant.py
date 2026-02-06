import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from qdrant_client import QdrantClient
from config import QDRANT_URL, QDRANT_API_KEY

def test_qdrant():
    print(f"Connecting to {QDRANT_URL}...")
    try:
        client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        print("Client type:", type(client))
        print("Client methods:", [m for m in dir(client) if not m.startswith('_')])
        
        # Test a dummy search
        try:
            client.search(collection_name="test", query_vector=[0.1]*384)
            print("Search method exists and called (errors expected if collection missing).")
        except Exception as e:
            print(f"Search call failed: {e}")

    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    test_qdrant()
