"""
Tests for RAG retriever functionality.

Tests the ChromaDB retriever, context builder, and related components
with mock data to ensure proper filtering and context assembly.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
import json

# Import the modules under test
from fundrunner.rag import (
    ChromaRetriever, 
    SearchResult, 
    SearchFilter,
    FilterOperation,
    ContextBuilder,
    ContextSource,
    SourceType,
    IndexConfig,
    EmbeddingModel,
    ChunkStrategy
)


class TestSearchResult(unittest.TestCase):
    """Test SearchResult functionality."""
    
    def test_search_result_creation(self):
        """Test basic SearchResult creation."""
        metadata = {
            "repo": "FundRunner",
            "file_path": "src/strategy.py", 
            "tags": ["strategy", "trading"],
            "source_type": "code"
        }
        
        result = SearchResult(
            content="def calculate_returns():\n    pass",
            metadata=metadata,
            distance=0.25,
            id="doc_123"
        )
        
        self.assertEqual(result.repo, "FundRunner")
        self.assertEqual(result.file_path, "src/strategy.py")
        self.assertEqual(result.tags, ["strategy", "trading"])
        self.assertEqual(result.distance, 0.25)
    
    def test_search_result_tags_parsing(self):
        """Test tags parsing from different formats."""
        # List format
        result1 = SearchResult(
            content="test", 
            metadata={"tags": ["a", "b", "c"]},
            distance=0.0,
            id="1"
        )
        self.assertEqual(result1.tags, ["a", "b", "c"])
        
        # String format
        result2 = SearchResult(
            content="test", 
            metadata={"tags": "a,b,c"},
            distance=0.0,
            id="2"
        )
        self.assertEqual(result2.tags, ["a", "b", "c"])
        
        # Empty
        result3 = SearchResult(
            content="test", 
            metadata={},
            distance=0.0,
            id="3"
        )
        self.assertEqual(result3.tags, [])


class TestSearchFilter(unittest.TestCase):
    """Test SearchFilter functionality."""
    
    def test_filter_operations(self):
        """Test different filter operations."""
        # Equals filter
        filter_eq = SearchFilter("repo", FilterOperation.EQUALS, "FundRunner")
        chroma_filter = filter_eq.to_chroma_filter()
        self.assertEqual(chroma_filter, {"repo": {"$eq": "FundRunner"}})
        
        # In filter
        filter_in = SearchFilter("tags", FilterOperation.IN, ["strategy", "trading"])
        chroma_filter = filter_in.to_chroma_filter()
        self.assertEqual(chroma_filter, {"tags": {"$in": ["strategy", "trading"]}})
        
        # Contains filter
        filter_contains = SearchFilter("file_path", FilterOperation.CONTAINS, "strategy")
        chroma_filter = filter_contains.to_chroma_filter()
        self.assertEqual(chroma_filter, {"file_path": {"$contains": "strategy"}})


class MockChromaCollection:
    """Mock ChromaDB collection for testing."""
    
    def __init__(self):
        self.documents = [
            {
                "id": "doc1",
                "content": "Trading strategy implementation with momentum indicators",
                "metadata": {
                    "repo": "FundRunner",
                    "file_path": "src/strategies/momentum.py",
                    "tags": ["strategy", "momentum"],
                    "source_type": "code"
                }
            },
            {
                "id": "doc2", 
                "content": "Risk management documentation for portfolio optimization",
                "metadata": {
                    "repo": "FundRunner",
                    "file_path": "docs/risk_management.md",
                    "tags": ["docs", "risk"],
                    "source_type": "docs"
                }
            },
            {
                "id": "doc3",
                "content": "Example backtest with Sharpe ratio calculation",
                "metadata": {
                    "repo": "OpenBB",
                    "file_path": "examples/backtest_example.py",
                    "tags": ["example", "backtest"],
                    "source_type": "example"
                }
            }
        ]
    
    def query(self, query_texts, n_results=10, where=None, include=None):
        """Mock query method."""
        # Simple mock implementation
        results = {
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
            "ids": [[]]
        }
        
        # Filter documents based on where clause
        filtered_docs = self.documents.copy()
        if where:
            filtered_docs = []
            for doc in self.documents:
                matches = True
                for field, condition in where.items():
                    if "$eq" in condition:
                        if doc["metadata"].get(field) != condition["$eq"]:
                            matches = False
                    elif "$in" in condition:
                        if doc["metadata"].get(field) not in condition["$in"]:
                            matches = False
                    elif "$contains" in condition:
                        field_value = doc["metadata"].get(field, "")
                        if condition["$contains"] not in str(field_value):
                            matches = False
                
                if matches:
                    filtered_docs.append(doc)
        
        # Return up to n_results
        for i, doc in enumerate(filtered_docs[:n_results]):
            results["documents"][0].append(doc["content"])
            results["metadatas"][0].append(doc["metadata"])
            results["distances"][0].append(0.1 * i)  # Mock distances
            results["ids"][0].append(doc["id"])
        
        return results
    
    def count(self):
        """Mock count method."""
        return len(self.documents)
    
    def get(self, ids, include=None):
        """Mock get method."""
        result = {"documents": [], "metadatas": []}
        for doc in self.documents:
            if doc["id"] in ids:
                result["documents"].append(doc["content"])
                result["metadatas"].append(doc["metadata"])
        return result


class TestChromaRetriever(unittest.TestCase):
    """Test ChromaRetriever functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_collection = MockChromaCollection()
    
    @patch('chromadb.HttpClient')
    def test_retriever_initialization(self, mock_client):
        """Test retriever initialization."""
        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance
        mock_client_instance.get_collection.return_value = self.mock_collection
        
        retriever = ChromaRetriever(
            chroma_host="localhost",
            chroma_port=8000,
            collection_name="test_collection"
        )
        
        self.assertTrue(retriever.is_connected())
        mock_client.assert_called_once()
    
    @patch('chromadb.HttpClient')
    def test_search_functionality(self, mock_client):
        """Test basic search functionality."""
        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance
        mock_client_instance.get_collection.return_value = self.mock_collection
        
        retriever = ChromaRetriever()
        retriever._collection = self.mock_collection
        
        results = retriever.search("trading strategy", limit=5)
        
        self.assertIsInstance(results, list)
        self.assertTrue(len(results) > 0)
        self.assertIsInstance(results[0], SearchResult)
    
    @patch('chromadb.HttpClient')
    def test_search_with_filters(self, mock_client):
        """Test search with various filters."""
        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance
        mock_client_instance.get_collection.return_value = self.mock_collection
        
        retriever = ChromaRetriever()
        retriever._collection = self.mock_collection
        
        # Test repo filter
        repo_filter = SearchFilter("repo", FilterOperation.EQUALS, "FundRunner")
        results = retriever.search("strategy", filters=[repo_filter])
        
        # Should only return FundRunner results
        for result in results:
            self.assertEqual(result.repo, "FundRunner")
    
    @patch('chromadb.HttpClient')
    def test_search_by_repo(self, mock_client):
        """Test search by repository."""
        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance
        mock_client_instance.get_collection.return_value = self.mock_collection
        
        retriever = ChromaRetriever()
        retriever._collection = self.mock_collection
        
        results = retriever.search_by_repo("documentation", "FundRunner")
        
        for result in results:
            self.assertEqual(result.repo, "FundRunner")
    
    @patch('chromadb.HttpClient')
    def test_batch_search(self, mock_client):
        """Test batch search functionality.""" 
        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance
        mock_client_instance.get_collection.return_value = self.mock_collection
        
        retriever = ChromaRetriever()
        retriever._collection = self.mock_collection
        
        queries = ["trading strategy", "risk management", "backtest"]
        batch_results = retriever.batch_search(queries, limit_per_query=3)
        
        self.assertEqual(len(batch_results), 3)
        for batch_result in batch_results:
            self.assertIn(batch_result.query, queries)
            self.assertIsInstance(batch_result.results, list)


class TestContextBuilder(unittest.TestCase):
    """Test ContextBuilder functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create sample search results
        self.search_results = [
            SearchResult(
                content="def calculate_momentum():\n    return price / sma",
                metadata={
                    "repo": "FundRunner",
                    "file_path": "src/indicators.py",
                    "tags": ["code", "indicators"],
                    "source_type": "code"
                },
                distance=0.1,
                id="doc1"
            ),
            SearchResult(
                content="Momentum trading strategies use price momentum to identify trends...",
                metadata={
                    "repo": "OpenBB",
                    "file_path": "docs/momentum.md", 
                    "tags": ["docs", "momentum"],
                    "source_type": "docs"
                },
                distance=0.2,
                id="doc2"
            ),
            SearchResult(
                content="# Example momentum strategy\nclass MomentumStrategy:\n    pass",
                metadata={
                    "repo": "Examples", 
                    "file_path": "examples/momentum_example.py",
                    "tags": ["example"],
                    "source_type": "example"
                },
                distance=0.15,
                id="doc3"
            )
        ]
    
    def test_context_builder_initialization(self):
        """Test context builder initialization."""
        builder = ContextBuilder(
            token_budget=1000,
            model="gpt-4",
            max_sources=10
        )
        
        self.assertEqual(builder.token_budget, 1000)
        self.assertEqual(builder.model, "gpt-4")
        self.assertEqual(builder.max_sources, 10)
    
    def test_source_type_classification(self):
        """Test source type classification."""
        builder = ContextBuilder()
        
        # Test code classification
        code_result = SearchResult(
            content="def test():\n    pass",
            metadata={"file_path": "test.py"},
            distance=0.0,
            id="test"
        )
        source_type = builder._classify_source_type(code_result)
        self.assertEqual(source_type, SourceType.CODE)
        
        # Test docs classification
        docs_result = SearchResult(
            content="This is documentation",
            metadata={"file_path": "README.md"},
            distance=0.0,
            id="test"
        )
        source_type = builder._classify_source_type(docs_result)
        self.assertEqual(source_type, SourceType.DOCUMENTATION)
    
    def test_context_building(self):
        """Test context building from search results."""
        builder = ContextBuilder(token_budget=2000, max_sources=5)
        
        context_result = builder.build_context(
            self.search_results,
            include_citations=True,
            include_metadata=True
        )
        
        self.assertIsNotNone(context_result.context)
        self.assertGreater(len(context_result.sources), 0)
        self.assertGreater(context_result.total_tokens, 0)
        self.assertLessEqual(context_result.total_tokens, builder.token_budget)
        
        # Check that citations are included
        self.assertTrue(any("Sources:" in context_result.context for _ in [1]))
    
    def test_deduplication(self):
        """Test content deduplication."""
        builder = ContextBuilder(deduplication_threshold=0.5)
        
        # Add duplicate content
        duplicate_results = self.search_results + [
            SearchResult(
                content="def calculate_momentum():\n    return price / sma",  # Exact duplicate
                metadata={"repo": "Test", "file_path": "duplicate.py"},
                distance=0.3,
                id="dup1"
            )
        ]
        
        context_result = builder.build_context(duplicate_results)
        
        # Should have fewer sources due to deduplication
        self.assertLess(len(context_result.sources), len(duplicate_results))
        self.assertGreater(context_result.deduplication_stats["original_sources"], 
                          context_result.deduplication_stats["final_used"])
    
    def test_token_budgeting(self):
        """Test token budgeting functionality.""" 
        # Create a builder with very small token budget
        builder = ContextBuilder(token_budget=100, max_sources=10)
        
        context_result = builder.build_context(self.search_results)
        
        # Should respect token budget
        self.assertLessEqual(context_result.total_tokens, 100)
        
        # Should indicate if truncated
        if context_result.total_tokens >= 95:  # Near budget limit
            self.assertTrue(context_result.truncated or len(context_result.sources) < len(self.search_results))


class TestIndexConfig(unittest.TestCase):
    """Test IndexConfig functionality."""
    
    def test_default_collections(self):
        """Test default collection configurations."""
        config = IndexConfig()
        
        self.assertIn("fundrunner_knowledge", config.list_collections())
        self.assertIn("openbb_docs", config.list_collections())
        self.assertIn("arbit_code", config.list_collections())
        
        # Test getting collection config
        fundrunner_config = config.get_collection_config("fundrunner_knowledge")
        self.assertIsNotNone(fundrunner_config)
        self.assertEqual(fundrunner_config.name, "fundrunner_knowledge")
    
    def test_config_serialization(self):
        """Test config serialization to/from dict."""
        config = IndexConfig()
        
        # Test collection config serialization
        fundrunner_config = config.get_collection_config("fundrunner_knowledge")
        config_dict = fundrunner_config.to_dict()
        
        self.assertIn("name", config_dict)
        self.assertIn("embedding_settings", config_dict)
        self.assertIn("chunk_settings", config_dict)
        
        # Test deserialization
        restored_config = config.__class__.from_dict(config_dict)
        self.assertEqual(restored_config.name, fundrunner_config.name)
    
    def test_config_validation(self):
        """Test configuration validation."""
        config = IndexConfig()
        
        issues = config.validate_config()
        
        # Default config should be valid
        self.assertEqual(len(issues), 0)
        
        # Test invalid config
        bad_config = config.get_collection_config("fundrunner_knowledge")
        bad_config.chunk_settings.chunk_size = -1
        config.add_collection_config(bad_config)
        
        issues = config.validate_config()
        self.assertGreater(len(issues), 0)
    
    def test_config_file_operations(self):
        """Test saving and loading config files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = os.path.join(temp_dir, "test_config.json")
            
            # Create and save config
            config1 = IndexConfig()
            config1.config_file = config_file
            config1.save_config()
            
            self.assertTrue(os.path.exists(config_file))
            
            # Load config from file
            config2 = IndexConfig(config_file)
            
            self.assertEqual(config1.list_collections(), config2.list_collections())


class TestIntegration(unittest.TestCase):
    """Integration tests for RAG components."""
    
    @patch('chromadb.HttpClient')
    def test_retriever_context_integration(self, mock_client):
        """Test integration between retriever and context builder."""
        # Setup mocks
        mock_collection = MockChromaCollection()
        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance
        mock_client_instance.get_collection.return_value = mock_collection
        
        # Create retriever and context builder
        retriever = ChromaRetriever()
        retriever._collection = mock_collection
        
        builder = ContextBuilder(token_budget=2000)
        
        # Test integrated workflow
        context_result = builder.build_context_from_retriever(
            retriever,
            "trading strategy implementation",
            limit=5
        )
        
        self.assertIsNotNone(context_result.context)
        self.assertGreater(len(context_result.sources), 0)
    
    def test_multi_query_context(self):
        """Test multi-query context building.""" 
        mock_collection = MockChromaCollection()
        
        with patch('chromadb.HttpClient') as mock_client:
            mock_client_instance = Mock()
            mock_client.return_value = mock_client_instance
            mock_client_instance.get_collection.return_value = mock_collection
            
            retriever = ChromaRetriever()
            retriever._collection = mock_collection
            
            builder = ContextBuilder(token_budget=3000)
            
            queries = ["momentum strategy", "risk management", "backtest results"]
            context_result = builder.build_multi_query_context(
                retriever,
                queries,
                results_per_query=2
            )
            
            self.assertIsNotNone(context_result.context)
            # Should have results from multiple queries
            self.assertGreater(len(context_result.sources), 2)


if __name__ == '__main__':
    unittest.main()
