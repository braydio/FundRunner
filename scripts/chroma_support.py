"""Support utilities for ChromaDB indexing operations.

This module provides functions for text processing, metadata extraction,
and document chunking for the semantic search infrastructure.
"""

import os
import re
from typing import Dict, List, Any
from pathlib import Path


def chunk_text(content: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Split text into overlapping chunks for better semantic search.
    
    Args:
        content: Text content to chunk
        chunk_size: Maximum characters per chunk
        overlap: Character overlap between chunks
        
    Returns:
        List of text chunks
    """
    if len(content) <= chunk_size:
        return [content]
    
    chunks = []
    start = 0
    
    while start < len(content):
        end = min(start + chunk_size, len(content))
        
        # Try to break at sentence boundaries
        if end < len(content):
            # Look for sentence endings
            for i in range(end - 1, start + chunk_size // 2, -1):
                if content[i] in '.!?':
                    end = i + 1
                    break
            # If no sentence boundary, look for word boundaries
            else:
                for i in range(end - 1, start + chunk_size // 2, -1):
                    if content[i].isspace():
                        end = i
                        break
        
        chunk = content[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        start = end - overlap if end < len(content) else end
    
    return chunks


def extract_metadata(file_path: str, content: str) -> Dict[str, Any]:
    """Extract metadata from file path and content.
    
    Args:
        file_path: Full path to the file
        content: File content
        
    Returns:
        Dictionary of metadata
    """
    path_obj = Path(file_path)
    
    # Basic file information
    metadata = {
        "relative_path": str(path_obj),
        "filename": path_obj.name,
        "file_extension": path_obj.suffix,
        "file_size": len(content),
        "repo": detect_repo_name(file_path),
    }
    
    # Language detection
    if path_obj.suffix == ".py":
        metadata["language"] = "python"
        metadata["tags"] = extract_python_tags(content)
        metadata["docstrings"] = extract_python_docstrings(content)
    elif path_obj.suffix in [".md", ".txt"]:
        metadata["language"] = "markdown" if path_obj.suffix == ".md" else "text"
        metadata["tags"] = extract_markdown_tags(content)
        metadata["docstrings"] = extract_markdown_summary(content)
    else:
        metadata["language"] = "unknown"
        metadata["tags"] = ""
        metadata["docstrings"] = ""
    
    # Module/component classification
    if "trading" in file_path.lower():
        metadata["component"] = "trading"
    elif "bot" in file_path.lower():
        metadata["component"] = "bot"
    elif "risk" in file_path.lower():
        metadata["component"] = "risk"
    elif "portfolio" in file_path.lower():
        metadata["component"] = "portfolio"
    elif "test" in file_path.lower():
        metadata["component"] = "test"
    elif "doc" in file_path.lower():
        metadata["component"] = "documentation"
    else:
        metadata["component"] = "core"
    
    return metadata


def detect_repo_name(file_path: str) -> str:
    """Detect repository name from file path.
    
    Args:
        file_path: Full file path
        
    Returns:
        Repository name or 'unknown'
    """
    path_parts = Path(file_path).parts
    
    # Look for known repository names
    repo_indicators = ["FundRunner", "OpenBB", "Arbit", "agents-for-openbb"]
    for part in path_parts:
        if part in repo_indicators:
            return part
    
    # Fallback: use the deepest directory that looks like a project
    for i, part in enumerate(path_parts):
        if any(indicator in part for indicator in ["Fund", "OpenBB", "Arbit", "agent"]):
            return part
    
    return "unknown"


def extract_python_tags(content: str) -> str:
    """Extract relevant tags from Python code.
    
    Args:
        content: Python source code
        
    Returns:
        Comma-separated string of tags
    """
    tags = []
    
    # Function and class names
    functions = re.findall(r'^def\s+(\w+)', content, re.MULTILINE)
    classes = re.findall(r'^class\s+(\w+)', content, re.MULTILINE)
    
    # Imports
    imports = re.findall(r'^(?:from\s+\w+\s+)?import\s+([\w\s,]+)', content, re.MULTILINE)
    
    # Trading-specific patterns
    trading_patterns = [
        "buy", "sell", "order", "trade", "portfolio", "risk", "strategy",
        "backtest", "indicator", "signal", "alpaca", "openbb"
    ]
    
    for pattern in trading_patterns:
        if pattern in content.lower():
            tags.append(pattern)
    
    # Add significant functions/classes
    tags.extend(functions[:3])  # First 3 functions
    tags.extend(classes[:2])    # First 2 classes
    
    return ",".join(tags[:10])  # Limit to 10 tags


def extract_python_docstrings(content: str) -> str:
    """Extract docstrings from Python code.
    
    Args:
        content: Python source code
        
    Returns:
        First docstring found, or empty string
    """
    # Look for module-level docstring
    module_docstring = re.search(r'^"""(.*?)"""', content, re.MULTILINE | re.DOTALL)
    if module_docstring:
        return module_docstring.group(1).strip()
    
    # Look for class or function docstring
    docstring = re.search(r'"""(.*?)"""', content, re.DOTALL)
    if docstring:
        return docstring.group(1).strip()
    
    return ""


def extract_markdown_tags(content: str) -> str:
    """Extract tags from markdown content.
    
    Args:
        content: Markdown content
        
    Returns:
        Comma-separated string of tags
    """
    tags = []
    
    # Headers
    headers = re.findall(r'^#+\s+(.*)', content, re.MULTILINE)
    
    # Trading/finance keywords
    finance_keywords = [
        "trading", "strategy", "portfolio", "risk", "backtest", "indicator",
        "openbb", "alpaca", "market", "stock", "option", "crypto"
    ]
    
    for keyword in finance_keywords:
        if keyword in content.lower():
            tags.append(keyword)
    
    # Add significant headers
    for header in headers[:3]:
        # Clean and add header words
        words = re.findall(r'\w+', header.lower())
        tags.extend([w for w in words if len(w) > 3][:2])
    
    return ",".join(tags[:8])


def extract_markdown_summary(content: str) -> str:
    """Extract summary from markdown content.
    
    Args:
        content: Markdown content
        
    Returns:
        First paragraph or description
    """
    # Remove headers and find first substantial paragraph
    lines = content.split('\n')
    summary_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith('#'):
            continue
        if len(line) > 20:  # Substantial content
            summary_lines.append(line)
            if len(' '.join(summary_lines)) > 200:
                break
    
    return ' '.join(summary_lines)[:300]


def get_git_info(file_path: str) -> Dict[str, str]:
    """Get git information for a file if available.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Dictionary with git info or empty dict
    """
    try:
        import subprocess
        
        result = subprocess.run(
            ['git', 'log', '-1', '--format=%H,%an,%ad', '--date=short', file_path],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(file_path)
        )
        
        if result.returncode == 0 and result.stdout.strip():
            commit_hash, author, date = result.stdout.strip().split(',', 2)
            return {
                "commit_sha": commit_hash[:8],
                "author": author,
                "last_modified": date
            }
    except Exception:
        pass
    
    return {}
