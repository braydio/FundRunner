"""Index project source files into a ChromaDB collection."""

import argparse
import os
import chromadb
from chromadb.errors import ChromaError, IDAlreadyExistsError
from chromadb.utils import embedding_functions
from chroma_support import chunk_text, extract_metadata

EXCLUDE_DIRS = {".venv", "__pycache__"}


def parse_args():
    parser = argparse.ArgumentParser(description="Index project files into ChromaDB")
    parser.add_argument("--source", default="backend", help="Source directory")
    parser.add_argument(
        "--collection", default=os.getenv("CHROMA_COLLECTION", "pynance-code")
    )
    parser.add_argument("--host", default=os.getenv("CHROMA_HOST", "localhost"))
    parser.add_argument("--port", type=int, default=int(os.getenv("CHROMA_PORT", 8055)))
    parser.add_argument(
        "--model", default=os.getenv("CHROMA_MODEL", "all-MiniLM-L6-v2")
    )
    parser.add_argument("--reindex", action="store_true")
    parser.add_argument("--diff-only", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    client = chromadb.HttpClient(host=args.host, port=args.port)
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=args.model
    )
    collection = client.get_or_create_collection(
        name=args.collection, embedding_function=embedding_fn
    )

    existing_ids = set()
    if not args.reindex:
        try:
            existing = collection.peek(limit=5000)
            existing_ids.update(existing["ids"])
            print(f"[CHROMA] Loaded {len(existing_ids)} existing document IDs")
        except ChromaError as e:
            print(f"[CHROMA] Warning: failed to peek collection: {e}")

    indexed_count = 0

    for root, dirs, files in os.walk(args.source):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for file in files:
            if not file.endswith((".py", ".md", ".txt")):
                continue
            path = os.path.join(root, file)
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read().replace("\x00", "")
                if not content.strip():
                    continue

                metadata_base = extract_metadata(path, content)
                chunks = chunk_text(content)
                tags = metadata_base.get("tags", "")

                for i, chunk in enumerate(chunks):
                    doc_id = f"{metadata_base['relative_path']}-{i}"
                    if not args.reindex and doc_id in existing_ids:
                        if args.diff_only:
                            continue
                    metadata = metadata_base.copy()
                    metadata["chunk_index"] = i
                    metadata["length"] = len(chunk)
                    metadata["source"] = metadata["relative_path"]

                    # Prepend tags for better context embedding
                    document_text = f"{tags}\n\n{chunk}" if tags else chunk

                    collection.add(
                        documents=[document_text],
                        metadatas=[metadata],
                        ids=[doc_id],
                    )
                    indexed_count += 1
                    if indexed_count % 50 == 0:
                        print(f"[CHROMA] Indexed {indexed_count} chunks...")

            except Exception as e:
                print(f"[CHROMA] Error processing '{path}': {e}")

    print(f"[CHROMA] Done. Indexed {indexed_count} new chunks to '{args.collection}'.")


if __name__ == "__main__":
    main()
