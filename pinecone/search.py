# search.py

import os
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
load_dotenv()

pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
index = pc.Index("3js-scenes")

model = SentenceTransformer("all-MiniLM-L6-v2")

def search(query, top_k=5):
    vec = model.encode(query).tolist()
    results = index.query(
        vector=vec,
        top_k=top_k,
        include_metadata=True
    )
    return results.matches

if __name__ == "__main__":
    q = input("Enter search description: ")
    matches = search(q)

    for m in matches:
        print("---")
        print("ID:", m.id)
        print("Score:", round(m.score, 3))
        print("Image:", m.metadata["image_path"])
        print("Text:", m.metadata["text"][:200], "...")
