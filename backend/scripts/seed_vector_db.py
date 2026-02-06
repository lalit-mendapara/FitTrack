
import sys
import os
import psycopg2
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from langchain_community.embeddings import OllamaEmbeddings
from tqdm import tqdm

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from config import QDRANT_URL, QDRANT_API_KEY, SQLALCHEMY_DATABASE_URL
except ImportError:
    # Fallback/Hardcode if config import fails outside app context
    QDRANT_URL = "http://localhost:6333"
    QDRANT_API_KEY = None
    SQLALCHEMY_DATABASE_URL = "postgresql://lalit:lalit84252@localhost:5432/fitness_track"

# Constants
EMBED_MODEL = "all-minilm"
FOOD_COLLECTION = "food_collection"
EXERCISE_COLLECTION = "exercise_collection"
VECTOR_SIZE = 384  # Size for all-minilm

def get_db_connection():
    return psycopg2.connect(SQLALCHEMY_DATABASE_URL)

def setup_collections(client):
    """Recreates collections."""
    collections = {
        FOOD_COLLECTION: VECTOR_SIZE,
        EXERCISE_COLLECTION: VECTOR_SIZE
    }
    
    for name, size in collections.items():
        print(f"Recreating collection: {name}")
        client.recreate_collection(
            collection_name=name,
            vectors_config=VectorParams(size=size, distance=Distance.COSINE)
        )

def seed_foods(client, embeddings):
    print("Fetching food items from DB...")
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT fdc_id, name, protein_g, calories_kcal, diet_type FROM food_items LIMIT 500") # Limit for speed test
    rows = cur.fetchall()
    conn.close()

    print(f"Found {len(rows)} food items. Generating embeddings...")
    
    points = []
    for row in tqdm(rows):
        fdc_id, name, protein, cals, diet = row
        # Text to embed
        text = f"{name} ({diet}). Protein: {protein}g, Calories: {cals}kcal"
        
        try:
            vector = embeddings.embed_query(text)
            
            points.append(PointStruct(
                id=int(fdc_id) if fdc_id.isdigit() else abs(hash(fdc_id)), # Ensure ID is int or uuid
                vector=vector,
                payload={
                    "name": name,
                    "protein": float(protein),
                    "calories": float(cals),
                    "diet_type": diet
                }
            ))
        except Exception as e:
            print(f"Skipping {name}: {e}")

    if points:
        client.upsert(
            collection_name=FOOD_COLLECTION,
            points=points
        )
        print(f"Uploaded {len(points)} food items.")

def seed_exercises(client, embeddings):
    print("Fetching exercises from DB...")
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT "ID", "Exercise Name", "Category", "Primary Muscle", "Difficulty" FROM exercises')
    rows = cur.fetchall()
    conn.close()

    print(f"Found {len(rows)} exercises. Generating embeddings...")
    
    points = []
    for row in tqdm(rows):
        ex_id, name, category, muscle, difficulty = row
        text = f"{name}. Category: {category}. Muscle: {muscle}. Level: {difficulty}"
        
        try:
            vector = embeddings.embed_query(text)
            
            points.append(PointStruct(
                id=ex_id,
                vector=vector,
                payload={
                    "name": name,
                    "category": category,
                    "muscle_group": muscle,
                    "difficulty": difficulty
                }
            ))
        except Exception as e:
            print(f"Skipping {name}: {e}")

    if points:
        client.upsert(
            collection_name=EXERCISE_COLLECTION,
            points=points
        )
        print(f"Uploaded {len(points)} exercises.")

def main():
    print("--- Seeding Vector DB ---")
    
    # 1. Connect
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    
    # 2. Embeddings
    print(f"Initializing Ollama Embeddings ({EMBED_MODEL})...")
    embeddings = OllamaEmbeddings(base_url="http://localhost:11434", model=EMBED_MODEL)
    
    # 3. Setup
    setup_collections(client)
    
    # 4. Seed
    seed_foods(client, embeddings)
    seed_exercises(client, embeddings)
    
    print("--- Seeding Complete ---")

if __name__ == "__main__":
    main()
