"""
Storage services for Nexus AI Assistant.

This module provides file and blob storage functionality.
"""

import os
import shutil
import logging
from typing import Dict, Any, Optional, BinaryIO, List

logger = logging.getLogger(__name__)

class StorageService:
    """File storage service."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize storage service.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.storage_dir = config.get('STORAGE_DIR', 'storage')
        self._ensure_storage_dir()
    
    def _ensure_storage_dir(self):
        """Ensure storage directory exists."""
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)
            logger.info(f"Created storage directory: {self.storage_dir}")
    
    def save_file(self, file_path: str, content: bytes) -> bool:
        """Save file to storage.
        
        Args:
            file_path: Relative path within storage directory
            content: File content as bytes
            
        Returns:
            True if successful, False otherwise
        """
        try:
            full_path = os.path.join(self.storage_dir, file_path)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            # Write file
            with open(full_path, 'wb') as f:
                f.write(content)
                
            logger.info(f"Saved file: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving file {file_path}: {str(e)}")
            return False
    
    def read_file(self, file_path: str) -> Optional[bytes]:
        """Read file from storage.
        
        Args:
            file_path: Relative path within storage directory
            
        Returns:
            File content as bytes, or None if file not found
        """
        try:
            full_path = os.path.join(self.storage_dir, file_path)
            if not os.path.exists(full_path):
                logger.warning(f"File not found: {file_path}")
                return None
                
            with open(full_path, 'rb') as f:
                content = f.read()
                
            logger.debug(f"Read file: {file_path}")
            return content
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {str(e)}")
            return None
    
    def delete_file(self, file_path: str) -> bool:
        """Delete file from storage.
        
        Args:
            file_path: Relative path within storage directory
            
        Returns:
            True if successful, False otherwise
        """
        try:
            full_path = os.path.join(self.storage_dir, file_path)
            if not os.path.exists(full_path):
                logger.warning(f"File not found for deletion: {file_path}")
                return False
                
            os.remove(full_path)
            logger.info(f"Deleted file: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error deleting file {file_path}: {str(e)}")
            return False
    
    def list_files(self, directory: str = "") -> List[str]:
        """List files in directory.
        
        Args:
            directory: Relative directory path within storage directory
            
        Returns:
            List of file paths
        """
        try:
            full_path = os.path.join(self.storage_dir, directory)
            if not os.path.exists(full_path):
                logger.warning(f"Directory not found: {directory}")
                return []
                
            files = []
            for root, _, filenames in os.walk(full_path):
                rel_root = os.path.relpath(root, self.storage_dir)
                for filename in filenames:
                    if rel_root == '.':
                        files.append(filename)
                    else:
                        files.append(os.path.join(rel_root, filename))
                        
            logger.debug(f"Listed {len(files)} files in {directory}")
            return files
        except Exception as e:
            logger.error(f"Error listing files in {directory}: {str(e)}")
            return []
