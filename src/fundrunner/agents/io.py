"""I/O utilities for safe file operations and diff generation in agent workflows."""

import os
import shutil
import tempfile
import difflib
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import logging

from fundrunner.utils.config import AGENTS_ARTIFACTS_DIR


logger = logging.getLogger(__name__)


def safe_read_file(file_path: str, encoding: str = "utf-8") -> Optional[str]:
    """Safely read a file with error handling.
    
    Args:
        file_path: Path to the file to read
        encoding: File encoding (default: utf-8)
        
    Returns:
        File contents or None if read failed
    """
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            return f.read()
    except (IOError, OSError, UnicodeDecodeError) as e:
        logger.error(f"Failed to read file {file_path}: {e}")
        return None


def safe_write_file(file_path: str, content: str, encoding: str = "utf-8", backup: bool = True) -> bool:
    """Safely write content to a file with backup and error handling.
    
    Args:
        file_path: Path to the file to write
        content: Content to write
        encoding: File encoding (default: utf-8)
        backup: Whether to create a backup of existing file
        
    Returns:
        True if write succeeded, False otherwise
    """
    try:
        # Create backup if file exists and backup is requested
        if backup and os.path.exists(file_path):
            backup_path = f"{file_path}.backup"
            shutil.copy2(file_path, backup_path)
            logger.debug(f"Created backup: {backup_path}")
        
        # Ensure parent directory exists
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Write content atomically using temp file
        with tempfile.NamedTemporaryFile(
            mode='w', 
            encoding=encoding, 
            dir=Path(file_path).parent,
            delete=False
        ) as temp_file:
            temp_file.write(content)
            temp_name = temp_file.name
        
        # Atomic move
        shutil.move(temp_name, file_path)
        logger.debug(f"Successfully wrote file: {file_path}")
        return True
        
    except (IOError, OSError, UnicodeEncodeError) as e:
        logger.error(f"Failed to write file {file_path}: {e}")
        # Clean up temp file if it exists
        try:
            if 'temp_name' in locals():
                os.unlink(temp_name)
        except OSError:
            pass
        return False


def generate_unified_diff(
    original_content: str,
    modified_content: str,
    original_label: str = "original",
    modified_label: str = "modified",
    context_lines: int = 3
) -> str:
    """Generate a unified diff between two text contents.
    
    Args:
        original_content: Original file content
        modified_content: Modified file content
        original_label: Label for original content in diff
        modified_label: Label for modified content in diff
        context_lines: Number of context lines around changes
        
    Returns:
        Unified diff string
    """
    original_lines = original_content.splitlines(keepends=True)
    modified_lines = modified_content.splitlines(keepends=True)
    
    diff = difflib.unified_diff(
        original_lines,
        modified_lines,
        fromfile=original_label,
        tofile=modified_label,
        n=context_lines
    )
    
    return ''.join(diff)


def apply_diff_patch(original_content: str, diff_content: str) -> Optional[str]:
    """Apply a unified diff patch to content.
    
    Note: This is a simplified implementation. For production use,
    consider using a more robust library like 'unidiff' or 'patch'.
    
    Args:
        original_content: Original content to patch
        diff_content: Unified diff content
        
    Returns:
        Patched content or None if patch failed
    """
    try:
        # This is a basic implementation - in practice you'd want
        # a more sophisticated diff application algorithm
        original_lines = original_content.splitlines()
        diff_lines = diff_content.splitlines()
        
        # Simple approach: extract additions and deletions
        # This is not a complete implementation of patch application
        logger.warning("apply_diff_patch is a simplified implementation")
        
        # For now, return None to indicate this needs proper implementation
        return None
        
    except Exception as e:
        logger.error(f"Failed to apply diff patch: {e}")
        return None


def create_artifact_file(
    content: str,
    filename: str,
    agent_name: str,
    task_id: str,
    file_type: str = "txt"
) -> Optional[str]:
    """Create an artifact file in the agents artifacts directory.
    
    Args:
        content: Content to write to artifact
        filename: Base filename (without extension)
        agent_name: Name of the agent creating the artifact
        task_id: ID of the task that generated the artifact
        file_type: File extension/type
        
    Returns:
        Path to created artifact file or None if creation failed
    """
    try:
        # Create artifacts directory structure
        artifacts_base = Path(AGENTS_ARTIFACTS_DIR)
        agent_dir = artifacts_base / agent_name / task_id
        agent_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename if file already exists
        artifact_path = agent_dir / f"{filename}.{file_type}"
        counter = 1
        while artifact_path.exists():
            artifact_path = agent_dir / f"{filename}_{counter}.{file_type}"
            counter += 1
        
        # Write content to artifact file
        if safe_write_file(str(artifact_path), content):
            logger.info(f"Created artifact: {artifact_path}")
            return str(artifact_path)
        else:
            return None
            
    except Exception as e:
        logger.error(f"Failed to create artifact file: {e}")
        return None


def list_artifacts(agent_name: Optional[str] = None, task_id: Optional[str] = None) -> List[str]:
    """List artifact files in the artifacts directory.
    
    Args:
        agent_name: Filter by agent name (optional)
        task_id: Filter by task ID (optional)
        
    Returns:
        List of artifact file paths
    """
    try:
        artifacts_base = Path(AGENTS_ARTIFACTS_DIR)
        if not artifacts_base.exists():
            return []
        
        artifacts = []
        
        if agent_name and task_id:
            # Specific agent and task
            search_path = artifacts_base / agent_name / task_id
            if search_path.exists():
                artifacts.extend([str(f) for f in search_path.rglob("*") if f.is_file()])
        elif agent_name:
            # Specific agent, all tasks
            search_path = artifacts_base / agent_name
            if search_path.exists():
                artifacts.extend([str(f) for f in search_path.rglob("*") if f.is_file()])
        else:
            # All agents and tasks
            artifacts.extend([str(f) for f in artifacts_base.rglob("*") if f.is_file()])
        
        return sorted(artifacts)
        
    except Exception as e:
        logger.error(f"Failed to list artifacts: {e}")
        return []


def clean_artifacts(
    older_than_days: int = 30,
    agent_name: Optional[str] = None,
    dry_run: bool = False
) -> Tuple[int, List[str]]:
    """Clean old artifact files.
    
    Args:
        older_than_days: Remove artifacts older than this many days
        agent_name: Clean only artifacts from specific agent (optional)
        dry_run: If True, only report what would be deleted
        
    Returns:
        Tuple of (files_deleted, list_of_deleted_paths)
    """
    import time
    
    try:
        artifacts_base = Path(AGENTS_ARTIFACTS_DIR)
        if not artifacts_base.exists():
            return 0, []
        
        cutoff_time = time.time() - (older_than_days * 24 * 60 * 60)
        deleted_files = []
        
        search_path = artifacts_base / agent_name if agent_name else artifacts_base
        
        for file_path in search_path.rglob("*"):
            if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                if dry_run:
                    logger.info(f"Would delete: {file_path}")
                else:
                    try:
                        file_path.unlink()
                        logger.debug(f"Deleted artifact: {file_path}")
                    except OSError as e:
                        logger.warning(f"Failed to delete {file_path}: {e}")
                        continue
                
                deleted_files.append(str(file_path))
        
        # Clean empty directories
        if not dry_run:
            for dir_path in search_path.rglob("*/"):
                try:
                    if dir_path.is_dir() and not any(dir_path.iterdir()):
                        dir_path.rmdir()
                        logger.debug(f"Removed empty directory: {dir_path}")
                except OSError:
                    pass  # Directory might not be empty or have permission issues
        
        logger.info(f"Cleaned {len(deleted_files)} artifact files")
        return len(deleted_files), deleted_files
        
    except Exception as e:
        logger.error(f"Failed to clean artifacts: {e}")
        return 0, []


def validate_file_path(file_path: str, allowed_extensions: Optional[List[str]] = None) -> bool:
    """Validate a file path for safety and allowed extensions.
    
    Args:
        file_path: Path to validate
        allowed_extensions: List of allowed file extensions (optional)
        
    Returns:
        True if path is valid and safe, False otherwise
    """
    try:
        path = Path(file_path).resolve()
        
        # Check for path traversal attempts
        if ".." in str(path):
            logger.warning(f"Path traversal attempt detected: {file_path}")
            return False
        
        # Check file extension if restrictions specified
        if allowed_extensions:
            extension = path.suffix.lower()
            if extension not in allowed_extensions:
                logger.warning(f"File extension {extension} not allowed: {file_path}")
                return False
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to validate file path {file_path}: {e}")
        return False


class DiffBuilder:
    """Builder class for creating structured diffs for code changes."""
    
    def __init__(self):
        self.changes: List[Dict[str, Any]] = []
    
    def add_file_change(
        self,
        file_path: str,
        original_content: str,
        modified_content: str,
        change_description: str = ""
    ) -> 'DiffBuilder':
        """Add a file change to the diff.
        
        Args:
            file_path: Path to the file being changed
            original_content: Original file content
            modified_content: Modified file content
            change_description: Description of the change
            
        Returns:
            Self for method chaining
        """
        diff = generate_unified_diff(
            original_content,
            modified_content,
            f"a/{file_path}",
            f"b/{file_path}"
        )
        
        self.changes.append({
            "file_path": file_path,
            "change_type": "modified",
            "description": change_description,
            "diff": diff,
            "original_lines": len(original_content.splitlines()),
            "modified_lines": len(modified_content.splitlines())
        })
        
        return self
    
    def add_new_file(
        self,
        file_path: str,
        content: str,
        change_description: str = ""
    ) -> 'DiffBuilder':
        """Add a new file to the diff.
        
        Args:
            file_path: Path to the new file
            content: File content
            change_description: Description of the change
            
        Returns:
            Self for method chaining
        """
        diff = generate_unified_diff(
            "",
            content,
            "/dev/null",
            f"b/{file_path}"
        )
        
        self.changes.append({
            "file_path": file_path,
            "change_type": "created",
            "description": change_description,
            "diff": diff,
            "original_lines": 0,
            "modified_lines": len(content.splitlines())
        })
        
        return self
    
    def add_deleted_file(
        self,
        file_path: str,
        original_content: str,
        change_description: str = ""
    ) -> 'DiffBuilder':
        """Add a deleted file to the diff.
        
        Args:
            file_path: Path to the deleted file
            original_content: Original file content
            change_description: Description of the change
            
        Returns:
            Self for method chaining
        """
        diff = generate_unified_diff(
            original_content,
            "",
            f"a/{file_path}",
            "/dev/null"
        )
        
        self.changes.append({
            "file_path": file_path,
            "change_type": "deleted",
            "description": change_description,
            "diff": diff,
            "original_lines": len(original_content.splitlines()),
            "modified_lines": 0
        })
        
        return self
    
    def build(self) -> Dict[str, Any]:
        """Build the complete diff structure.
        
        Returns:
            Dictionary containing all changes and summary statistics
        """
        total_additions = sum(
            change["modified_lines"] - change["original_lines"]
            for change in self.changes
            if change["modified_lines"] > change["original_lines"]
        )
        
        total_deletions = sum(
            change["original_lines"] - change["modified_lines"]
            for change in self.changes
            if change["original_lines"] > change["modified_lines"]
        )
        
        return {
            "changes": self.changes,
            "summary": {
                "files_changed": len(self.changes),
                "total_additions": total_additions,
                "total_deletions": total_deletions,
                "created_files": len([c for c in self.changes if c["change_type"] == "created"]),
                "modified_files": len([c for c in self.changes if c["change_type"] == "modified"]),
                "deleted_files": len([c for c in self.changes if c["change_type"] == "deleted"]),
            },
            "unified_diff": "\n".join(change["diff"] for change in self.changes)
        }
    
    def reset(self) -> 'DiffBuilder':
        """Reset the diff builder to empty state.
        
        Returns:
            Self for method chaining
        """
        self.changes.clear()
        return self
