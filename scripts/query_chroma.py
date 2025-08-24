# scripts/query_chroma.py
"""Query a Chroma collection for semantically similar documents."""

import argparse
import os
import sys

import chromadb
from chromadb.errors import ChromaError
from chromadb.utils import embedding_functions

DEFAULT_COLLECTION = os.getenv("CHROMA_COLLECTION", "pynance-code")
DEFAULT_COUNT = int(os.getenv("CHROMA_RESULT_COUNT", 3))
DEFAULT_HOST = os.getenv("CHROMA_HOST", "localhost")
DEFAULT_PORT = int(os.getenv("CHROMA_PORT", 8055))
DEFAULT_MODEL = os.getenv("CHROMA_MODEL", "all-MiniLM-L6-v2")

parser = argparse.ArgumentParser(description="Query ChromaDB for similar documents.")
parser.add_argument("query", nargs="+", help="Query text")
parser.add_argument("-n", "--count", type=int, default=DEFAULT_COUNT)
parser.add_argument("--collection", default=DEFAULT_COLLECTION)
parser.add_argument("--host", default=DEFAULT_HOST)
parser.add_argument("--port", type=int, default=DEFAULT_PORT)
parser.add_argument("--model", default=DEFAULT_MODEL)
parser.add_argument("--show-distance", action="store_true")
args = parser.parse_args()

query_text = " ".join(args.query)

try:
    client = chromadb.HttpClient(host=args.host, port=args.port)
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=args.model
    )
    collection = client.get_or_create_collection(
        name=args.collection, embedding_function=embedding_fn
    )
except ChromaError as e:
    print(f"[ERROR] Failed to connect to ChromaDB: {e}")
    sys.exit(1)

results = collection.query(query_texts=[query_text], n_results=args.count)

print("\n[RESULTS]")
for i, doc in enumerate(results["documents"][0]):
    meta = results["metadatas"][0][i]
    source = meta.get("source") or meta.get("relative_path", "unknown")
    tags = meta.get("tags", "")
    summary = meta.get("docstrings", "")
    distance_info = (
        f" (distance: {results['distances'][0][i]:.4f})" if args.show_distance else ""
    )

    print(f"{i + 1}. {doc.strip()[:300]}...{distance_info}")
    print(f"   └─ Source: {source}")
    if tags:
        print(f"   └─ Tags: {tags}")
    if summary:
        print(f"   └─ Summary: {summary[:150]}")
    print()
