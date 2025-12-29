"""
FundRunner RAG Module

This package provides Retrieval-Augmented Generation (RAG) functionality for the
FundRunner platform, enabling semantic search and context building from indexed
knowledge bases including code repositories, documentation, and financial data.

Key Components:
- ChromaRetriever: Interface to ChromaDB for semantic search
- ContextBuilder: Intelligent context assembly with token budgeting
- IndexConfig: Centralized configuration for embeddings and collections

The RAG system supports filtering by repository, file paths, tags, and other metadata
to provide relevant context for AI agents working on trading strategies, research,
and code generation tasks.
"""

from .retriever import ChromaRetriever, SearchResult, BatchSearchResult
from .context_builder import ContextBuilder, ContextResult, ContextSource
from .index_config import IndexConfig, ChunkSettings, EmbeddingSettings

__all__ = [
    "ChromaRetriever",
    "SearchResult", 
    "BatchSearchResult",
    "ContextBuilder",
    "ContextResult",
    "ContextSource", 
    "IndexConfig",
    "ChunkSettings",
    "EmbeddingSettings",
]
