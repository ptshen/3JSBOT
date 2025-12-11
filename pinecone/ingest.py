# ingest.py

import os
import glob
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
index = pc.Index("3js-scenes")

model = SentenceTransformer("all-MiniLM-L6-v2")

BASE_DIR = Path(__file__).resolve().parent.parent   # 3JSBOT/
DATA_DIR = BASE_DIR / "image_to_prompt" / "screenshots"


def read_md(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def ingest():
    md_files = glob.glob(str(DATA_DIR / "*.md"))
    vectors = []

    for md_path in md_files:
        md_path = Path(md_path)
        base = md_path.stem  # filename without extension
        jpg_path = DATA_DIR / f"{base}.jpg"

        if not jpg_path.exists():
            print(f"⚠ No .jpg found for {base}, skipping")
            continue

        text = read_md(md_path)
        emb = model.encode(text).tolist()

        # Store only the filename, not full path
        vectors.append({
            "id": base,
            "values": emb,
            "metadata": {
                "text": text,
                "image_filename": f"{base}.jpg",
                "md_filename": f"{base}.md"
            }
        })

    if vectors:
        print(f"Uploading {len(vectors)} items to Pinecone...")
        index.upsert(vectors)
        print("Done.")

if __name__ == "__main__":
    ingest()
