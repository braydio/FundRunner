"""
ChromaDB Retriever for Semantic Search

Provides a high-level interface to ChromaDB with support for filtered queries,
batch operations, and metadata-based search narrowing for the FundRunner RAG system.
"""

import os
import logging
from typing import List, Dict, Any, Optional, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
import chromadb
from chromadb.config import Settings
from chromadb.errors import NotFoundError

# Configure logging
logger = logging.getLogger(__name__)


class FilterOperation(Enum):
    """Supported filter operations for metadata queries."""
    EQUALS = "eq"
    NOT_EQUALS = "ne" 
    IN = "in"
    NOT_IN = "nin"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"


@dataclass
class SearchResult:
    """Result from a single semantic search query."""
    content: str
    metadata: Dict[str, Any]
    distance: float
    id: str
    
    @property
    def repo(self) -> Optional[str]:
        """Get repository name from metadata."""
        return self.metadata.get("repo")
    
    @property
    def file_path(self) -> Optional[str]:
        """Get file path from metadata.""" 
        return self.metadata.get("file_path") or self.metadata.get("path")
    
    @property
    def tags(self) -> List[str]:
        """Get tags from metadata."""
        tags = self.metadata.get("tags", [])
        if isinstance(tags, str):
            return tags.split(",") if tags else []
        return tags or []


@dataclass
class BatchSearchResult:
    """Result from batch semantic search queries."""
    query: str
    results: List[SearchResult]
    total_found: int
    
    def __len__(self) -> int:
        return len(self.results)
    
    def __iter__(self):
        return iter(self.results)


@dataclass 
class SearchFilter:
    """Filter specification for narrowing search results."""
    field: str
    operation: FilterOperation
    value: Union[str, List[str], int, bool]
    
    def to_chroma_filter(self) -> Dict[str, Any]:
        """Convert to ChromaDB filter format."""
        if self.operation == FilterOperation.EQUALS:
            return {self.field: {"$eq": self.value}}
        elif self.operation == FilterOperation.NOT_EQUALS:
            return {self.field: {"$ne": self.value}}
        elif self.operation == FilterOperation.IN:
            return {self.field: {"$in": self.value}}
        elif self.operation == FilterOperation.NOT_IN:
            return {self.field: {"$nin": self.value}}
        elif self.operation == FilterOperation.CONTAINS:
            return {self.field: {"$contains": self.value}}
        else:
            # For starts_with/ends_with, use regex-like patterns
            if self.operation == FilterOperation.STARTS_WITH:
                return {self.field: {"$regex": f"^{self.value}"}}
            elif self.operation == FilterOperation.ENDS_WITH:
                return {self.field: {"$regex": f"{self.value}$"}}
        
        return {}


class ChromaRetriever:
    """
    ChromaDB client wrapper for semantic search with filtering capabilities.
    
    Supports querying with filters by repository, file paths, tags, and other metadata
    to narrow context retrieval for RAG applications.
    """
    
    def __init__(
        self,
        chroma_host: Optional[str] = None,
        chroma_port: Optional[int] = None,
        collection_name: str = "fundrunner_knowledge",
        embedding_model: str = "all-MiniLM-L6-v2"
    ):
        """
        Initialize ChromaDB retriever.
        
        Args:
            chroma_host: ChromaDB server host (default from CHROMA_HOST env)
            chroma_port: ChromaDB server port (default from CHROMA_PORT env) 
            collection_name: Name of the collection to query
            embedding_model: Sentence transformer model for embeddings
        """
        self.chroma_host = chroma_host or os.getenv("CHROMA_HOST", "localhost")
        self.chroma_port = chroma_port or int(os.getenv("CHROMA_PORT", "8000"))
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        
        # Initialize client
        self._client = None
        self._collection = None
        self._connect()
    
    def _connect(self) -> None:
        """Establish connection to ChromaDB server."""
        try:
            settings = Settings(
                chroma_server_host=self.chroma_host,
                chroma_server_http_port=self.chroma_port,
                chroma_api_impl="chromadb.api.fastapi.FastAPI",
                chroma_server_ssl_enabled=False
            )
            
            self._client = chromadb.HttpClient(
                host=self.chroma_host, 
                port=self.chroma_port,
                settings=settings
            )
            
            # Get or create collection
            try:
                self._collection = self._client.get_collection(
                    name=self.collection_name
                )
                logger.info(f"Connected to collection '{self.collection_name}'")
            except NotFoundError:
                logger.warning(f"Collection '{self.collection_name}' not found")
                self._collection = None
                
        except Exception as e:
            logger.error(f"Failed to connect to ChromaDB: {e}")
            self._client = None
            self._collection = None
    
    def is_connected(self) -> bool:
        """Check if connected to ChromaDB and collection exists."""
        return self._client is not None and self._collection is not None
    
    def list_collections(self) -> List[str]:
        """List available collections."""
        if not self._client:
            return []
        
        try:
            collections = self._client.list_collections()
            return [c.name for c in collections]
        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            return []
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the current collection."""
        if not self._collection:
            return {"connected": False}
        
        try:
            count = self._collection.count()
            return {
                "connected": True,
                "collection_name": self.collection_name,
                "document_count": count,
                "embedding_model": self.embedding_model
            }
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {"connected": False, "error": str(e)}
    
    def search(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[List[SearchFilter]] = None,
        include_metadata: bool = True,
        min_relevance_score: float = 0.0
    ) -> List[SearchResult]:
        """
        Search for relevant documents using semantic similarity.
        
        Args:
            query: Search query text
            limit: Maximum number of results to return
            filters: List of metadata filters to apply
            include_metadata: Whether to include document metadata
            min_relevance_score: Minimum relevance score threshold
            
        Returns:
            List of SearchResult objects
        """
        if not self._collection:
            logger.warning("No collection available for search")
            return []
        
        try:
            # Build ChromaDB where clause from filters
            where_clause = {}
            if filters:
                for search_filter in filters:
                    filter_dict = search_filter.to_chroma_filter()
                    where_clause.update(filter_dict)
            
            # Execute query
            results = self._collection.query(
                query_texts=[query],
                n_results=limit,
                where=where_clause if where_clause else None,
                include=["documents", "metadatas", "distances"]
            )
            
            # Parse results
            search_results = []
            if results["documents"] and results["documents"][0]:
                documents = results["documents"][0]
                metadatas = results["metadatas"][0] if results["metadatas"] else [{}] * len(documents)
                distances = results["distances"][0] if results["distances"] else [0.0] * len(documents)
                ids = results["ids"][0] if results["ids"] else [f"doc_{i}" for i in range(len(documents))]
                
                for doc, metadata, distance, doc_id in zip(documents, metadatas, distances, ids):
                    # Convert distance to relevance score (lower distance = higher relevance)
                    relevance_score = 1.0 - min(distance, 1.0)
                    
                    if relevance_score >= min_relevance_score:
                        search_results.append(SearchResult(
                            content=doc,
                            metadata=metadata or {},
                            distance=distance,
                            id=doc_id
                        ))
            
            logger.debug(f"Search for '{query}' returned {len(search_results)} results")
            return search_results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def search_by_repo(
        self,
        query: str,
        repo: str,
        limit: int = 10,
        **kwargs
    ) -> List[SearchResult]:
        """Search within a specific repository."""
        repo_filter = SearchFilter("repo", FilterOperation.EQUALS, repo)
        return self.search(query, limit, filters=[repo_filter], **kwargs)
    
    def search_by_path_pattern(
        self,
        query: str, 
        path_pattern: str,
        limit: int = 10,
        **kwargs
    ) -> List[SearchResult]:
        """Search for documents matching a file path pattern."""
        path_filter = SearchFilter("file_path", FilterOperation.CONTAINS, path_pattern)
        return self.search(query, limit, filters=[path_filter], **kwargs)
    
    def search_by_tags(
        self,
        query: str,
        tags: List[str],
        match_any: bool = True,
        limit: int = 10,
        **kwargs
    ) -> List[SearchResult]:
        """Search for documents with specific tags."""
        if match_any:
            # Use IN operation to match any of the tags
            tag_filter = SearchFilter("tags", FilterOperation.IN, tags)
        else:
            # For match_all, we'd need multiple filters (not implemented in simple version)
            # For now, just use the first tag with CONTAINS
            tag_filter = SearchFilter("tags", FilterOperation.CONTAINS, tags[0])
        
        return self.search(query, limit, filters=[tag_filter], **kwargs)
    
    def batch_search(
        self,
        queries: List[str],
        limit_per_query: int = 5,
        filters: Optional[List[SearchFilter]] = None,
        **kwargs
    ) -> List[BatchSearchResult]:
        """
        Execute multiple search queries in batch.
        
        Args:
            queries: List of search query strings
            limit_per_query: Maximum results per query
            filters: Common filters to apply to all queries
            
        Returns:
            List of BatchSearchResult objects
        """
        batch_results = []
        
        for query in queries:
            results = self.search(
                query,
                limit=limit_per_query,
                filters=filters,
                **kwargs
            )
            
            batch_results.append(BatchSearchResult(
                query=query,
                results=results,
                total_found=len(results)
            ))
        
        return batch_results
    
    def get_document_by_id(self, doc_id: str) -> Optional[SearchResult]:
        """Retrieve a specific document by its ID."""
        if not self._collection:
            return None
        
        try:
            result = self._collection.get(
                ids=[doc_id],
                include=["documents", "metadatas"]
            )
            
            if result["documents"] and result["documents"][0]:
                return SearchResult(
                    content=result["documents"][0],
                    metadata=result["metadatas"][0] if result["metadatas"] else {},
                    distance=0.0,  # Direct retrieval has no distance
                    id=doc_id
                )
        except Exception as e:
            logger.error(f"Failed to get document {doc_id}: {e}")
        
        return None
    
    def get_similar_documents(
        self,
        doc_id: str,
        limit: int = 5,
        filters: Optional[List[SearchFilter]] = None
    ) -> List[SearchResult]:
        """Find documents similar to a given document ID."""
        # First get the document content
        doc = self.get_document_by_id(doc_id)
        if not doc:
            return []
        
        # Use its content as the search query
        results = self.search(
            doc.content,
            limit=limit + 1,  # +1 to account for the original document
            filters=filters
        )
        
        # Filter out the original document
        return [r for r in results if r.id != doc_id][:limit]


def create_repo_filter(repo_name: str) -> SearchFilter:
    """Convenience function to create a repository filter."""
    return SearchFilter("repo", FilterOperation.EQUALS, repo_name)


def create_path_filter(path_pattern: str, exact_match: bool = False) -> SearchFilter:
    """Convenience function to create a file path filter."""
    operation = FilterOperation.EQUALS if exact_match else FilterOperation.CONTAINS
    return SearchFilter("file_path", operation, path_pattern)


def create_tags_filter(tags: List[str], match_any: bool = True) -> SearchFilter:
    """Convenience function to create a tags filter.""" 
    operation = FilterOperation.IN if match_any else FilterOperation.CONTAINS
    value = tags if match_any else tags[0]  # Simplified for match_all
    return SearchFilter("tags", operation, value)
