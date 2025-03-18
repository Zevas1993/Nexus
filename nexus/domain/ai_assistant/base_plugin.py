"""
Base interface for AI assistant plugins.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class AIPlugin(ABC):
    """Base class for AI assistant plugins."""
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        """Initialize AI plugin.
        
        Args:
            name: Plugin name
            config: Optional configuration
        """
        self.name = name
        self.config = config or {}
        self.enabled = True
        
    @abstractmethod
    async def process(self, request: str, **kwargs) -> Dict[str, Any]:
        """Process a request.
        
        Args:
            request: Request string
            **kwargs: Additional parameters
            
        Returns:
            Processing result
        """
        pass
        
    def get_supported_roles(self) -> List[str]:
        """Get roles supported by this plugin.
        
        Returns:
            List of role identifiers
        """
        return []
        
    def get_priority(self) -> int:
        """Get plugin priority (1-10).
        
        Returns:
            Priority value (higher is more important)
        """
        return 5
        
    def get_resource_requirements(self) -> Dict[str, Any]:
        """Get resource requirements.
        
        Returns:
            Dictionary with resource requirements
        """
        return {
            "ram_mb": 256,
            "cpu_percent": 10,
            "gpu_mb": 0
        }
        
    async def initialize(self) -> bool:
        """Initialize plugin.
        
        Returns:
            True if initialization succeeded
        """
        return True
        
    async def shutdown(self) -> None:
        """Shutdown plugin."""
        pass
