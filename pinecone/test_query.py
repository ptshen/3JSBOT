import os
from pathlib import Path
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
index = pc.Index("3js-scenes")

# Load the same model used in ingest.py
model = SentenceTransformer("all-MiniLM-L6-v2")

# Base directory (3JSBOT/)
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "image_to_prompt" / "screenshots"


def search_scene(query_text, top_k=3):
    embedding = model.encode(query_text).tolist()

    result = index.query(
        vector=embedding,
        top_k=top_k,
        include_metadata=True
    )
    return result


if __name__ == "__main__":
    query = input("Describe the scene you want to find: ")

    results = search_scene(query)

    print("\n--- Top Matches ---")
    for match in results["matches"]:
        score = match["score"]
        md_text = match["metadata"]["text"]
        image_file = match["metadata"]["image_path"]

        print(f"\nScore: {score:.4f}")
        print(f"Markdown content (first 200 chars): {md_text[:200]}...")
        print(f"Image: {image_file}")


    print("\nDone.")
