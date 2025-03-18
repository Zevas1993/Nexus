"""
Registry for AI assistant plugins.
"""
import logging
from typing import Dict, Any, List, Optional

from .base_plugin import AIPlugin

logger = logging.getLogger(__name__)

class AIPluginRegistry:
    """Registry for AI assistant plugins with role management."""
    
    # Role types
    ROLES = {
        "COMPLETION": "Real-time code completion",
        "ANALYSIS": "Code quality and security analysis", 
        "DOCUMENTATION": "Documentation generation",
        "REFACTORING": "Code refactoring suggestions",
        "TESTING": "Test generation and validation"
    }
    
    def __init__(self):
        """Initialize plugin registry."""
        self.plugins: Dict[str, AIPlugin] = {}
        self.role_assignments: Dict[str, List[str]] = {role: [] for role in self.ROLES}
        self.plugin_priorities: Dict[str, int] = {}
        
    def register_plugin(self, plugin: AIPlugin, roles: List[str], priority: int = 5) -> None:
        """Register a plugin for specific roles with priority.
        
        Args:
            plugin: Plugin instance
            roles: List of roles
            priority: Priority value (1-10)
        """
        self.plugins[plugin.name] = plugin
        self.plugin_priorities[plugin.name] = priority
        
        # Assign to requested roles
        for role in roles:
            if role in self.ROLES:
                self.role_assignments[role].append(plugin.name)
                # Sort role plugins by priority
                self.role_assignments[role].sort(
                    key=lambda p: self.plugin_priorities[p], 
                    reverse=True
                )
                logger.info(f"Registered plugin {plugin.name} for role {role}")
            else:
                logger.warning(f"Unknown role {role} requested by plugin {plugin.name}")
    
    def get_plugins_for_role(self, role: str) -> List[AIPlugin]:
        """Get all plugins assigned to a role, ordered by priority.
        
        Args:
            role: Role identifier
            
        Returns:
            List of plugin instances
        """
        if role not in self.ROLES:
            return []
            
        return [self.plugins[name] for name in self.role_assignments[role] 
                if name in self.plugins]
                
    def get_plugin(self, name: str) -> Optional[AIPlugin]:
        """Get a plugin by name.
        
        Args:
            name: Plugin name
            
        Returns:
            Plugin instance or None
        """
        return self.plugins.get(name)
        
    def get_all_plugins(self) -> List[AIPlugin]:
        """Get all registered plugins.
        
        Returns:
            List of all plugin instances
        """
        return list(self.plugins.values())
        
    def get_available_roles(self) -> Dict[str, str]:
        """Get all available roles.
        
        Returns:
            Dictionary of role identifiers to descriptions
        """
        return self.ROLES.copy()
