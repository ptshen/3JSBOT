# pinecone_setup.py

from pinecone import Pinecone, ServerlessSpec, CloudProvider, AwsRegion
from sentence_transformers import SentenceTransformer
import os
from dotenv import load_dotenv
load_dotenv()

pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])

index_name = "3js-scenes"

# Use local model to get vector size
model = SentenceTransformer("all-MiniLM-L6-v2")
dim = model.get_sentence_embedding_dimension()

if index_name not in pc.list_indexes().names():
    print("Creating index...")
    pc.create_index(
        name=index_name,
        dimension=dim,
        metric="cosine",
        spec=ServerlessSpec(
            cloud=CloudProvider.AWS,
            region=AwsRegion.US_EAST_1
        )
    )
else:
    print("Index already exists.")
