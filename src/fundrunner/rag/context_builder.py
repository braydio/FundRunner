"""
Context Builder with Token Budgeting

Merges code snippets, documentation, and examples with intelligent token budgeting,
deduplication, and source citation for RAG-enhanced AI agents.
"""

import os
import re
import hashlib
import logging
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import tiktoken

from .retriever import SearchResult, ChromaRetriever

# Configure logging
logger = logging.getLogger(__name__)


class SourceType(Enum):
    """Types of sources in the context."""
    CODE = "code"
    DOCUMENTATION = "docs" 
    EXAMPLE = "example"
    CONFIG = "config"
    TEST = "test"
    UNKNOWN = "unknown"


@dataclass
class ContextSource:
    """A source contributing to the context."""
    content: str
    source_type: SourceType
    file_path: Optional[str] = None
    repo: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    relevance_score: float = 0.0
    token_count: int = 0
    content_hash: str = field(init=False)
    
    def __post_init__(self):
        """Calculate content hash for deduplication."""
        self.content_hash = hashlib.md5(self.content.encode()).hexdigest()
    
    @property
    def citation(self) -> str:
        """Generate a citation string for this source."""
        parts = []
        if self.repo:
            parts.append(f"repo:{self.repo}")
        if self.file_path:
            parts.append(f"path:{self.file_path}")
        if self.tags:
            parts.append(f"tags:{','.join(self.tags)}")
        
        return f"[{' | '.join(parts)}]" if parts else "[unknown source]"


@dataclass
class ContextResult:
    """Result from context building operation."""
    context: str
    sources: List[ContextSource]
    total_tokens: int
    token_budget_used: float  # Percentage of budget used
    truncated: bool = False
    deduplication_stats: Dict[str, int] = field(default_factory=dict)
    
    @property
    def source_citations(self) -> List[str]:
        """Get citation strings for all sources."""
        return [source.citation for source in self.sources]
    
    @property
    def unique_repos(self) -> Set[str]:
        """Get unique repositories referenced."""
        return {source.repo for source in self.sources if source.repo}
    
    @property
    def source_type_counts(self) -> Dict[str, int]:
        """Count sources by type."""
        counts = {}
        for source in self.sources:
            source_type = source.source_type.value
            counts[source_type] = counts.get(source_type, 0) + 1
        return counts


class TokenCounter:
    """Utility for counting tokens using tiktoken."""
    
    def __init__(self, model: str = "gpt-4"):
        """Initialize token counter for specified model."""
        try:
            self.encoder = tiktoken.encoding_for_model(model)
        except KeyError:
            # Fallback to cl100k_base encoding (used by GPT-4)
            self.encoder = tiktoken.get_encoding("cl100k_base")
        
        self.model = model
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        try:
            return len(self.encoder.encode(text))
        except Exception as e:
            logger.warning(f"Token counting failed: {e}. Using character approximation.")
            # Rough approximation: 4 characters per token
            return len(text) // 4
    
    def truncate_to_budget(self, text: str, token_budget: int) -> Tuple[str, bool]:
        """Truncate text to fit within token budget."""
        current_tokens = self.count_tokens(text)
        if current_tokens <= token_budget:
            return text, False
        
        # Binary search to find the right truncation point
        lines = text.split('\n')
        left, right = 0, len(lines)
        best_text = ""
        
        while left < right:
            mid = (left + right + 1) // 2
            candidate = '\n'.join(lines[:mid])
            if self.count_tokens(candidate) <= token_budget:
                best_text = candidate
                left = mid
            else:
                right = mid - 1
        
        return best_text, True


class ContextBuilder:
    """
    Builds contextual information from search results with intelligent token budgeting,
    deduplication, and source citation.
    """
    
    def __init__(
        self,
        token_budget: int = 8000,
        model: str = "gpt-4",
        max_sources: int = 20,
        deduplication_threshold: float = 0.8
    ):
        """
        Initialize context builder.
        
        Args:
            token_budget: Maximum tokens for the final context
            model: Language model for token counting
            max_sources: Maximum number of sources to include
            deduplication_threshold: Similarity threshold for content deduplication
        """
        self.token_budget = token_budget
        self.model = model
        self.max_sources = max_sources
        self.deduplication_threshold = deduplication_threshold
        
        self.token_counter = TokenCounter(model)
        self._source_type_patterns = {
            SourceType.CODE: [r'\.py$', r'\.js$', r'\.ts$', r'\.go$', r'\.java$', r'\.cpp$', r'\.c$'],
            SourceType.DOCUMENTATION: [r'\.md$', r'\.rst$', r'README', r'\.txt$'],
            SourceType.EXAMPLE: [r'example', r'demo', r'tutorial', r'sample'],
            SourceType.CONFIG: [r'\.yaml$', r'\.yml$', r'\.json$', r'\.toml$', r'config'],
            SourceType.TEST: [r'test_', r'_test\.', r'/tests?/']
        }
    
    def _classify_source_type(self, search_result: SearchResult) -> SourceType:
        """Classify the type of source based on file path and metadata."""
        file_path = search_result.file_path or ""
        tags = search_result.tags
        
        # Check tags first
        for tag in tags:
            tag_lower = tag.lower()
            if tag_lower in ['code', 'implementation']:
                return SourceType.CODE
            elif tag_lower in ['docs', 'documentation']:
                return SourceType.DOCUMENTATION
            elif tag_lower in ['example', 'demo', 'tutorial']:
                return SourceType.EXAMPLE
            elif tag_lower in ['config', 'configuration']:
                return SourceType.CONFIG
            elif tag_lower in ['test', 'testing']:
                return SourceType.TEST
        
        # Check file path patterns
        for source_type, patterns in self._source_type_patterns.items():
            for pattern in patterns:
                if re.search(pattern, file_path, re.IGNORECASE):
                    return source_type
        
        return SourceType.UNKNOWN
    
    def _calculate_content_similarity(self, content1: str, content2: str) -> float:
        """Calculate similarity between two content strings."""
        # Simple Jaccard similarity based on words
        words1 = set(content1.lower().split())
        words2 = set(content2.lower().split())
        
        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def _deduplicate_sources(self, sources: List[ContextSource]) -> List[ContextSource]:
        """Remove duplicate or very similar content."""
        deduplicated = []
        seen_hashes = set()
        similarity_groups = []
        
        for source in sources:
            # Skip exact duplicates by hash
            if source.content_hash in seen_hashes:
                continue
            seen_hashes.add(source.content_hash)
            
            # Check for high similarity with existing sources
            is_similar = False
            for existing in deduplicated:
                similarity = self._calculate_content_similarity(source.content, existing.content)
                if similarity >= self.deduplication_threshold:
                    # Keep the one with higher relevance score
                    if source.relevance_score > existing.relevance_score:
                        deduplicated.remove(existing)
                        deduplicated.append(source)
                    is_similar = True
                    break
            
            if not is_similar:
                deduplicated.append(source)
        
        return deduplicated
    
    def _prioritize_sources(self, sources: List[ContextSource]) -> List[ContextSource]:
        """Prioritize sources by relevance, type, and other factors."""
        # Define type priorities (higher is better)
        type_priorities = {
            SourceType.CODE: 3,
            SourceType.EXAMPLE: 3,
            SourceType.DOCUMENTATION: 2,
            SourceType.CONFIG: 1,
            SourceType.TEST: 1,
            SourceType.UNKNOWN: 0
        }
        
        def priority_score(source: ContextSource) -> Tuple[float, int, int]:
            type_priority = type_priorities.get(source.source_type, 0)
            # Prefer shorter content for better token efficiency
            length_penalty = -len(source.content) / 1000
            return (source.relevance_score, type_priority, length_penalty)
        
        return sorted(sources, key=priority_score, reverse=True)
    
    def _format_source_for_context(self, source: ContextSource, include_metadata: bool = True) -> str:
        """Format a source for inclusion in context."""
        parts = []
        
        if include_metadata:
            # Add source header with citation
            header = f"Source: {source.citation}"
            if source.source_type != SourceType.UNKNOWN:
                header += f" (type: {source.source_type.value})"
            parts.append(header)
            parts.append("-" * len(header))
        
        # Add content with appropriate formatting
        if source.source_type == SourceType.CODE:
            # Wrap code in code blocks
            parts.append("```")
            parts.append(source.content)
            parts.append("```")
        else:
            parts.append(source.content)
        
        if include_metadata:
            parts.append("")  # Add spacing between sources
        
        return "\n".join(parts)
    
    def build_context(
        self,
        search_results: List[SearchResult],
        include_citations: bool = True,
        include_metadata: bool = True,
        preserve_order: bool = False
    ) -> ContextResult:
        """
        Build context from search results with token budgeting and deduplication.
        
        Args:
            search_results: List of search results to build context from
            include_citations: Whether to include source citations
            include_metadata: Whether to include source metadata in context
            preserve_order: Whether to preserve original result order
            
        Returns:
            ContextResult with formatted context and metadata
        """
        if not search_results:
            return ContextResult(
                context="No relevant context found.",
                sources=[],
                total_tokens=0,
                token_budget_used=0.0
            )
        
        # Convert search results to context sources
        sources = []
        for result in search_results:
            source_type = self._classify_source_type(result)
            token_count = self.token_counter.count_tokens(result.content)
            
            source = ContextSource(
                content=result.content,
                source_type=source_type,
                file_path=result.file_path,
                repo=result.repo,
                tags=result.tags,
                relevance_score=1.0 - result.distance,  # Convert distance to relevance
                token_count=token_count
            )
            sources.append(source)
        
        # Deduplication
        original_count = len(sources)
        sources = self._deduplicate_sources(sources)
        deduplicated_count = len(sources)
        
        # Prioritization (unless preserving order)
        if not preserve_order:
            sources = self._prioritize_sources(sources)
        
        # Limit number of sources
        if len(sources) > self.max_sources:
            sources = sources[:self.max_sources]
        
        # Build context within token budget
        context_parts = []
        used_sources = []
        current_tokens = 0
        truncated = False
        
        # Reserve tokens for citations if needed
        citation_tokens = 0
        if include_citations:
            sample_citations = [s.citation for s in sources[:5]]
            citation_text = "\n\nSources:\n" + "\n".join(f"- {c}" for c in sample_citations)
            citation_tokens = self.token_counter.count_tokens(citation_text)
        
        available_budget = self.token_budget - citation_tokens
        
        for source in sources:
            # Format source for context
            formatted_source = self._format_source_for_context(source, include_metadata)
            source_tokens = self.token_counter.count_tokens(formatted_source)
            
            # Check if we can fit this source
            if current_tokens + source_tokens <= available_budget:
                context_parts.append(formatted_source)
                used_sources.append(source)
                current_tokens += source_tokens
            else:
                # Try to fit a truncated version
                remaining_budget = available_budget - current_tokens
                if remaining_budget > 100:  # Only if we have reasonable space left
                    truncated_content, was_truncated = self.token_counter.truncate_to_budget(
                        source.content, remaining_budget - 50  # Reserve space for formatting
                    )
                    
                    if truncated_content:
                        truncated_source = ContextSource(
                            content=truncated_content,
                            source_type=source.source_type,
                            file_path=source.file_path,
                            repo=source.repo,
                            tags=source.tags,
                            relevance_score=source.relevance_score,
                            token_count=self.token_counter.count_tokens(truncated_content)
                        )
                        
                        formatted_truncated = self._format_source_for_context(truncated_source, include_metadata)
                        context_parts.append(formatted_truncated + "\n[Content truncated...]")
                        used_sources.append(truncated_source)
                        truncated = True
                
                break  # Stop adding sources
        
        # Assemble final context
        context = "\n".join(context_parts)
        
        # Add citations if requested
        if include_citations and used_sources:
            citations = [source.citation for source in used_sources]
            context += f"\n\nSources:\n" + "\n".join(f"- {citation}" for citation in citations)
        
        # Final token count
        final_tokens = self.token_counter.count_tokens(context)
        budget_used = final_tokens / self.token_budget * 100
        
        return ContextResult(
            context=context,
            sources=used_sources,
            total_tokens=final_tokens,
            token_budget_used=budget_used,
            truncated=truncated,
            deduplication_stats={
                "original_sources": original_count,
                "after_deduplication": deduplicated_count,
                "final_used": len(used_sources)
            }
        )
    
    def build_context_from_retriever(
        self,
        retriever: ChromaRetriever,
        query: str,
        **search_kwargs
    ) -> ContextResult:
        """
        Build context by querying a retriever directly.
        
        Args:
            retriever: ChromaRetriever instance
            query: Search query
            **search_kwargs: Additional arguments for retriever.search()
            
        Returns:
            ContextResult with formatted context
        """
        search_results = retriever.search(query, **search_kwargs)
        return self.build_context(search_results)
    
    def build_multi_query_context(
        self,
        retriever: ChromaRetriever,
        queries: List[str],
        results_per_query: int = 5,
        **search_kwargs
    ) -> ContextResult:
        """
        Build context from multiple related queries.
        
        Args:
            retriever: ChromaRetriever instance
            queries: List of search queries
            results_per_query: Maximum results per query
            **search_kwargs: Additional arguments for retriever.search()
            
        Returns:
            ContextResult with combined context from all queries
        """
        all_results = []
        
        for query in queries:
            results = retriever.search(
                query,
                limit=results_per_query,
                **search_kwargs
            )
            all_results.extend(results)
        
        return self.build_context(all_results)
    
    def get_budget_stats(self) -> Dict[str, Any]:
        """Get statistics about token budgeting."""
        return {
            "token_budget": self.token_budget,
            "model": self.model,
            "max_sources": self.max_sources,
            "deduplication_threshold": self.deduplication_threshold
        }
