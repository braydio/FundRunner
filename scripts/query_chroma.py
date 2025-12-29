# scripts/query_chroma.py
"""Query a Chroma collection for semantically similar documents with filtering."""

import argparse
import json
import os
import sys
from typing import Dict, Any, Optional
import chromadb
from chromadb.errors import ChromaError
from chromadb.utils import embedding_functions

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from fundrunner.rag import ChromaRetriever, ContextBuilder, SearchFilter, FilterOperation
except ImportError:
    # Fallback if RAG module not available
    ChromaRetriever = None
    ContextBuilder = None
    SearchFilter = None
    FilterOperation = None

DEFAULT_COLLECTION = os.getenv("CHROMA_COLLECTION", "fundrunner_knowledge")
DEFAULT_COUNT = int(os.getenv("CHROMA_RESULT_COUNT", 5))
DEFAULT_HOST = os.getenv("CHROMA_HOST", "localhost")
DEFAULT_PORT = int(os.getenv("CHROMA_PORT", "8000"))
DEFAULT_MODEL = os.getenv("CHROMA_MODEL", "all-MiniLM-L6-v2")

def parse_filter_arg(filter_str: str) -> Dict[str, str]:
    """Parse filter argument in format 'field=value'."""
    if '=' not in filter_str:
        raise ValueError(f"Invalid filter format '{filter_str}'. Use 'field=value'")
    
    field, value = filter_str.split('=', 1)
    return {field.strip(): value.strip()}

def build_filters(args) -> Optional[Dict[str, Any]]:
    """Build ChromaDB where clause from command line arguments."""
    where_clause = {}
    
    # Add repository filter
    if args.filter_repo:
        repos = [repo.strip() for repo in args.filter_repo.split(',')]
        if len(repos) == 1:
            where_clause["repo"] = {"$eq": repos[0]}
        else:
            where_clause["repo"] = {"$in": repos}
    
    # Add path-like filter 
    if args.path_like:
        # Support multiple path patterns
        paths = [path.strip() for path in args.path_like.split(',')]
        if len(paths) == 1:
            where_clause["file_path"] = {"$contains": paths[0]}
        else:
            # Use $or for multiple path patterns
            where_clause["$or"] = [{"file_path": {"$contains": path}} for path in paths]
    
    # Add tags filter
    if args.tags:
        tags = [tag.strip() for tag in args.tags.split(',')]
        if len(tags) == 1:
            where_clause["tags"] = {"$contains": tags[0]}
        else:
            # Use $in for any of the tags
            where_clause["tags"] = {"$in": tags}
    
    # Add custom filters
    if args.filter:
        for filter_arg in args.filter:
            try:
                filter_dict = parse_filter_arg(filter_arg)
                for field, value in filter_dict.items():
                    # Try to parse as JSON for complex values
                    try:
                        parsed_value = json.loads(value)
                    except json.JSONDecodeError:
                        parsed_value = value
                    
                    where_clause[field] = {"$eq": parsed_value}
            except ValueError as e:
                print(f"Warning: {e}")
    
    return where_clause if where_clause else None

parser = argparse.ArgumentParser(
    description="Query ChromaDB for similar documents with filtering capabilities.",
    epilog="""Examples:
  %(prog)s "trading strategy" --filter-repo=FundRunner --count=10
  %(prog)s "momentum indicators" --tags=strategy,indicator --show-snippets
  %(prog)s "risk management" --path-like=risk --filter-repo=OpenBB
  %(prog)s "backtest" --filter source_type=code --context --token-budget=4000
    """,
    formatter_class=argparse.RawDescriptionHelpFormatter
)

parser.add_argument("query", nargs="+", help="Query text")
parser.add_argument("-n", "--count", type=int, default=DEFAULT_COUNT,
                    help="Number of results to return")
parser.add_argument("--collection", default=DEFAULT_COLLECTION,
                    help="ChromaDB collection name")
parser.add_argument("--host", default=DEFAULT_HOST,
                    help="ChromaDB server host")
parser.add_argument("--port", type=int, default=DEFAULT_PORT,
                    help="ChromaDB server port")
parser.add_argument("--model", default=DEFAULT_MODEL,
                    help="Embedding model name")

# Display options
parser.add_argument("--show-distance", action="store_true",
                    help="Show relevance distances")
parser.add_argument("--show-snippets", action="store_true",
                    help="Show longer content snippets")
parser.add_argument("--show-metadata", action="store_true",
                    help="Show full metadata for each result")

# Filtering options
parser.add_argument("--filter-repo", metavar="REPO",
                    help="Filter by repository name(s), comma-separated")
parser.add_argument("--path-like", metavar="PATTERN",
                    help="Filter by file path pattern(s), comma-separated")
parser.add_argument("--tags", metavar="TAGS",
                    help="Filter by tags, comma-separated")
parser.add_argument("--filter", action="append", metavar="FIELD=VALUE",
                    help="Custom filter in format 'field=value' (repeatable)")

# Context building options
parser.add_argument("--context", action="store_true",
                    help="Build formatted context with token budgeting")
parser.add_argument("--token-budget", type=int, default=8000,
                    help="Token budget for context building")
parser.add_argument("--no-citations", action="store_true",
                    help="Don't include source citations in context")

args = parser.parse_args()

query_text = " ".join(args.query)

# Use enhanced RAG functionality if available
if ChromaRetriever and args.context:
    try:
        retriever = ChromaRetriever(
            chroma_host=args.host,
            chroma_port=args.port,
            collection_name=args.collection,
            embedding_model=args.model
        )
        
        if not retriever.is_connected():
            print(f"[ERROR] Failed to connect to ChromaDB collection '{args.collection}'")
            sys.exit(1)
        
        # Build search filters from command line args
        filters = []
        if args.filter_repo:
            filters.append(SearchFilter("repo", FilterOperation.IN, args.filter_repo.split(',')))
        if args.path_like:
            filters.append(SearchFilter("file_path", FilterOperation.CONTAINS, args.path_like))
        if args.tags:
            filters.append(SearchFilter("tags", FilterOperation.IN, args.tags.split(',')))
        
        # Search with filters
        search_results = retriever.search(
            query_text,
            limit=args.count,
            filters=filters or None
        )
        
        if args.context:
            # Build context with token budgeting
            context_builder = ContextBuilder(
                token_budget=args.token_budget,
                model="gpt-4",  # For token counting
                max_sources=args.count
            )
            
            context_result = context_builder.build_context(
                search_results,
                include_citations=not args.no_citations,
                include_metadata=True
            )
            
            print(f"\n[CONTEXT] ({context_result.total_tokens} tokens, {context_result.token_budget_used:.1f}% of budget)")
            print("=" * 80)
            print(context_result.context)
            print("=" * 80)
            
            if context_result.truncated:
                print("\n[WARNING] Context was truncated to fit token budget")
            
            print(f"\n[STATS]")
            print(f"Sources used: {len(context_result.sources)}")
            print(f"Unique repos: {', '.join(context_result.unique_repos) or 'None'}")
            print(f"Source types: {context_result.source_type_counts}")
            print(f"Deduplication: {context_result.deduplication_stats}")
            
        else:
            # Show individual results
            print(f"\n[RESULTS] ({len(search_results)} found)")
            for i, result in enumerate(search_results):
                distance_info = f" (distance: {result.distance:.4f})" if args.show_distance else ""
                
                snippet_length = 500 if args.show_snippets else 200
                content_snippet = result.content.strip()[:snippet_length]
                if len(result.content) > snippet_length:
                    content_snippet += "..."
                
                print(f"{i + 1}. {content_snippet}{distance_info}")
                print(f"   └─ Source: {result.file_path or 'unknown'}")
                if result.repo:
                    print(f"   └─ Repo: {result.repo}")
                if result.tags:
                    print(f"   └─ Tags: {', '.join(result.tags)}")
                
                if args.show_metadata:
                    print(f"   └─ Metadata: {result.metadata}")
                print()
    
    except Exception as e:
        print(f"[ERROR] Enhanced search failed: {e}")
        print("Falling back to basic ChromaDB query...")
        args.context = False  # Disable context for fallback

# Fallback to basic ChromaDB query
if not ChromaRetriever or not args.context:
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
    
    # Build where clause for filtering
    where_clause = build_filters(args)
    
    try:
        results = collection.query(
            query_texts=[query_text], 
            n_results=args.count,
            where=where_clause
        )
    except Exception as e:
        print(f"[ERROR] Query failed: {e}")
        if where_clause:
            print("This might be due to unsupported filters. Trying without filters...")
            results = collection.query(query_texts=[query_text], n_results=args.count)
        else:
            sys.exit(1)
    
    if not results["documents"] or not results["documents"][0]:
        print("\n[NO RESULTS] No documents found matching your query.")
        if where_clause:
            print("Try removing some filters to get broader results.")
        sys.exit(0)
    
    print(f"\n[RESULTS] ({len(results['documents'][0])} found)")
    if where_clause:
        print(f"Applied filters: {where_clause}")
    
    for i, doc in enumerate(results["documents"][0]):
        meta = results["metadatas"][0][i] if results.get("metadatas") else {}
        
        # Try different metadata field names
        source = (meta.get("file_path") or meta.get("source") or 
                 meta.get("relative_path", "unknown"))
        tags = meta.get("tags", "")
        summary = meta.get("docstrings", "")
        repo = meta.get("repo", "")
        
        distance_info = (
            f" (distance: {results['distances'][0][i]:.4f})" if args.show_distance else ""
        )
        
        snippet_length = 500 if args.show_snippets else 300
        content_snippet = doc.strip()[:snippet_length]
        if len(doc) > snippet_length:
            content_snippet += "..."
        
        print(f"{i + 1}. {content_snippet}{distance_info}")
        print(f"   └─ Source: {source}")
        if repo:
            print(f"   └─ Repo: {repo}")
        if tags:
            print(f"   └─ Tags: {tags}")
        if summary:
            print(f"   └─ Summary: {summary[:150]}")
        
        if args.show_metadata:
            print(f"   └─ Full metadata: {meta}")
        print()
