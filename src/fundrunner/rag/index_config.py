"""
Index Configuration for RAG System

Centralized configuration for ChromaDB collections, embedding models, 
chunk sizes, and other RAG-related settings.
"""

import os
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import json


class EmbeddingModel(Enum):
    """Supported embedding models."""
    MINI_LM_L6_V2 = "all-MiniLM-L6-v2"
    MINI_LM_L12_V2 = "all-MiniLM-L12-v2"
    MPNET_BASE_V2 = "all-mpnet-base-v2"
    DISTILBERT_BASE = "all-distilbert-base-v1"
    
    @property
    def dimensions(self) -> int:
        """Get the embedding dimensions for this model."""
        dimensions_map = {
            self.MINI_LM_L6_V2: 384,
            self.MINI_LM_L12_V2: 384,
            self.MPNET_BASE_V2: 768,
            self.DISTILBERT_BASE: 768,
        }
        return dimensions_map[self]


class ChunkStrategy(Enum):
    """Strategies for chunking documents."""
    FIXED_SIZE = "fixed_size"
    SEMANTIC = "semantic"
    PARAGRAPH = "paragraph"
    SENTENCE = "sentence"


@dataclass
class ChunkSettings:
    """Settings for document chunking."""
    strategy: ChunkStrategy = ChunkStrategy.FIXED_SIZE
    chunk_size: int = 1000
    chunk_overlap: int = 200
    min_chunk_size: int = 100
    max_chunk_size: int = 2000
    separators: List[str] = field(default_factory=lambda: ["\n\n", "\n", " ", ""])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "strategy": self.strategy.value,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "min_chunk_size": self.min_chunk_size,
            "max_chunk_size": self.max_chunk_size,
            "separators": self.separators
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChunkSettings':
        """Create from dictionary."""
        return cls(
            strategy=ChunkStrategy(data.get("strategy", ChunkStrategy.FIXED_SIZE.value)),
            chunk_size=data.get("chunk_size", 1000),
            chunk_overlap=data.get("chunk_overlap", 200),
            min_chunk_size=data.get("min_chunk_size", 100),
            max_chunk_size=data.get("max_chunk_size", 2000),
            separators=data.get("separators", ["\n\n", "\n", " ", ""])
        )


@dataclass
class EmbeddingSettings:
    """Settings for embedding generation."""
    model: EmbeddingModel = EmbeddingModel.MINI_LM_L6_V2
    normalize_embeddings: bool = True
    batch_size: int = 32
    device: str = "cpu"  # or "cuda" if available
    cache_embeddings: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "model": self.model.value,
            "normalize_embeddings": self.normalize_embeddings,
            "batch_size": self.batch_size,
            "device": self.device,
            "cache_embeddings": self.cache_embeddings
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EmbeddingSettings':
        """Create from dictionary."""
        return cls(
            model=EmbeddingModel(data.get("model", EmbeddingModel.MINI_LM_L6_V2.value)),
            normalize_embeddings=data.get("normalize_embeddings", True),
            batch_size=data.get("batch_size", 32),
            device=data.get("device", "cpu"),
            cache_embeddings=data.get("cache_embeddings", True)
        )


@dataclass
class CollectionConfig:
    """Configuration for a specific ChromaDB collection."""
    name: str
    description: str = ""
    embedding_settings: EmbeddingSettings = field(default_factory=EmbeddingSettings)
    chunk_settings: ChunkSettings = field(default_factory=ChunkSettings)
    metadata_fields: List[str] = field(default_factory=lambda: ["repo", "file_path", "tags", "source_type"])
    filterable_fields: List[str] = field(default_factory=lambda: ["repo", "tags", "source_type"])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "embedding_settings": self.embedding_settings.to_dict(),
            "chunk_settings": self.chunk_settings.to_dict(),
            "metadata_fields": self.metadata_fields,
            "filterable_fields": self.filterable_fields
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CollectionConfig':
        """Create from dictionary."""
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            embedding_settings=EmbeddingSettings.from_dict(data.get("embedding_settings", {})),
            chunk_settings=ChunkSettings.from_dict(data.get("chunk_settings", {})),
            metadata_fields=data.get("metadata_fields", ["repo", "file_path", "tags", "source_type"]),
            filterable_fields=data.get("filterable_fields", ["repo", "tags", "source_type"])
        )


class IndexConfig:
    """
    Central configuration manager for RAG indexing and retrieval.
    
    Manages collections, embedding models, chunk sizes, and other settings
    for the ChromaDB-based RAG system.
    """
    
    # Default collections
    DEFAULT_COLLECTIONS = {
        "fundrunner_knowledge": CollectionConfig(
            name="fundrunner_knowledge",
            description="FundRunner codebase and documentation",
            embedding_settings=EmbeddingSettings(
                model=EmbeddingModel.MINI_LM_L6_V2,
                normalize_embeddings=True
            ),
            chunk_settings=ChunkSettings(
                strategy=ChunkStrategy.FIXED_SIZE,
                chunk_size=800,
                chunk_overlap=150
            ),
            metadata_fields=["repo", "file_path", "tags", "source_type", "commit_sha"],
            filterable_fields=["repo", "tags", "source_type", "file_path"]
        ),
        "openbb_docs": CollectionConfig(
            name="openbb_docs",
            description="OpenBB documentation and examples",
            embedding_settings=EmbeddingSettings(
                model=EmbeddingModel.MINI_LM_L6_V2
            ),
            chunk_settings=ChunkSettings(
                strategy=ChunkStrategy.PARAGRAPH,
                chunk_size=1200,
                chunk_overlap=200
            ),
            metadata_fields=["repo", "file_path", "tags", "doc_type", "url"],
            filterable_fields=["repo", "tags", "doc_type"]
        ),
        "arbit_code": CollectionConfig(
            name="arbit_code",
            description="Arbit arbitrage trading code repository",
            embedding_settings=EmbeddingSettings(
                model=EmbeddingModel.MPNET_BASE_V2  # Higher quality for code
            ),
            chunk_settings=ChunkSettings(
                strategy=ChunkStrategy.SEMANTIC,
                chunk_size=600,  # Smaller for code
                chunk_overlap=100
            ),
            metadata_fields=["repo", "file_path", "tags", "source_type", "language"],
            filterable_fields=["repo", "tags", "source_type", "language"]
        )
    }
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_file: Path to configuration file (JSON format)
        """
        self.config_file = config_file or os.getenv("RAG_CONFIG_FILE")
        self.collections: Dict[str, CollectionConfig] = {}
        
        # Load configuration
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from file or use defaults."""
        if self.config_file and os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
                
                # Load collections from config
                for name, collection_data in config_data.get("collections", {}).items():
                    self.collections[name] = CollectionConfig.from_dict(collection_data)
                
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Warning: Failed to load config from {self.config_file}: {e}")
                self.collections = self.DEFAULT_COLLECTIONS.copy()
        else:
            # Use default collections
            self.collections = self.DEFAULT_COLLECTIONS.copy()
    
    def save_config(self, config_file: Optional[str] = None) -> None:
        """Save current configuration to file."""
        file_path = config_file or self.config_file
        if not file_path:
            raise ValueError("No config file path specified")
        
        config_data = {
            "collections": {
                name: config.to_dict() 
                for name, config in self.collections.items()
            }
        }
        
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as f:
            json.dump(config_data, f, indent=2)
    
    def get_collection_config(self, name: str) -> Optional[CollectionConfig]:
        """Get configuration for a specific collection."""
        return self.collections.get(name)
    
    def add_collection_config(self, config: CollectionConfig) -> None:
        """Add or update a collection configuration."""
        self.collections[config.name] = config
    
    def remove_collection_config(self, name: str) -> bool:
        """Remove a collection configuration."""
        if name in self.collections:
            del self.collections[name]
            return True
        return False
    
    def list_collections(self) -> List[str]:
        """List all configured collection names."""
        return list(self.collections.keys())
    
    def get_default_collection(self) -> str:
        """Get the name of the default collection."""
        return "fundrunner_knowledge"
    
    def get_embedding_model_info(self, model: EmbeddingModel) -> Dict[str, Any]:
        """Get information about an embedding model."""
        return {
            "name": model.value,
            "dimensions": model.dimensions,
            "type": "sentence_transformers"
        }
    
    def get_chroma_connection_settings(self) -> Dict[str, Any]:
        """Get ChromaDB connection settings from environment."""
        return {
            "host": os.getenv("CHROMA_HOST", "localhost"),
            "port": int(os.getenv("CHROMA_PORT", "8000")),
            "ssl_enabled": os.getenv("CHROMA_SSL_ENABLED", "false").lower() == "true",
            "auth_token": os.getenv("CHROMA_AUTH_TOKEN")
        }
    
    def validate_config(self) -> List[str]:
        """Validate the current configuration and return any issues."""
        issues = []
        
        if not self.collections:
            issues.append("No collections configured")
        
        for name, config in self.collections.items():
            # Check required fields
            if not config.name:
                issues.append(f"Collection '{name}' missing name")
            
            # Check chunk settings
            if config.chunk_settings.chunk_size <= 0:
                issues.append(f"Collection '{name}' has invalid chunk_size")
            
            if config.chunk_settings.chunk_overlap >= config.chunk_settings.chunk_size:
                issues.append(f"Collection '{name}' has overlap >= chunk_size")
            
            # Check embedding settings
            if config.embedding_settings.batch_size <= 0:
                issues.append(f"Collection '{name}' has invalid batch_size")
        
        return issues
    
    @classmethod
    def create_default_config(cls, config_file: str) -> 'IndexConfig':
        """Create a default configuration file."""
        config = cls()
        config.config_file = config_file
        config.save_config()
        return config


# Convenience functions for common configurations

def get_finance_optimized_config() -> CollectionConfig:
    """Get a configuration optimized for financial code and documentation."""
    return CollectionConfig(
        name="finance_knowledge",
        description="Financial trading code and documentation",
        embedding_settings=EmbeddingSettings(
            model=EmbeddingModel.MPNET_BASE_V2,  # Higher quality for technical content
            normalize_embeddings=True,
            batch_size=16  # Smaller batches for stability
        ),
        chunk_settings=ChunkSettings(
            strategy=ChunkStrategy.SEMANTIC,
            chunk_size=800,  # Good balance for code and docs
            chunk_overlap=150,
            min_chunk_size=50,
            max_chunk_size=1500
        ),
        metadata_fields=["repo", "file_path", "tags", "source_type", "language", "complexity"],
        filterable_fields=["repo", "tags", "source_type", "language"]
    )


def get_documentation_config() -> CollectionConfig:
    """Get a configuration optimized for documentation."""
    return CollectionConfig(
        name="documentation",
        description="Documentation and guides",
        embedding_settings=EmbeddingSettings(
            model=EmbeddingModel.MINI_LM_L6_V2,  # Fast and good for text
            normalize_embeddings=True
        ),
        chunk_settings=ChunkSettings(
            strategy=ChunkStrategy.PARAGRAPH,
            chunk_size=1500,  # Longer chunks for documentation
            chunk_overlap=250,
            separators=["\n\n", "\n", ". ", " "]
        ),
        metadata_fields=["repo", "file_path", "tags", "doc_type", "section"],
        filterable_fields=["repo", "tags", "doc_type", "section"]
    )


def get_code_config() -> CollectionConfig:
    """Get a configuration optimized for code."""
    return CollectionConfig(
        name="code",
        description="Source code and examples",
        embedding_settings=EmbeddingSettings(
            model=EmbeddingModel.MPNET_BASE_V2,  # Better for code understanding
            normalize_embeddings=True,
            batch_size=16
        ),
        chunk_settings=ChunkSettings(
            strategy=ChunkStrategy.SEMANTIC,
            chunk_size=600,  # Smaller chunks for focused code snippets
            chunk_overlap=100,
            min_chunk_size=100,
            separators=["\n\nclass ", "\n\ndef ", "\n\n", "\n"]  # Code-aware separators
        ),
        metadata_fields=["repo", "file_path", "tags", "source_type", "language", "functions", "classes"],
        filterable_fields=["repo", "tags", "source_type", "language"]
    )
