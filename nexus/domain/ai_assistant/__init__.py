"""
AI Assistant package for Nexus AI.

This package provides AI-powered coding assistance through a plugin-based architecture,
supporting multiple providers and capabilities like code completion and analysis.
"""

from .base_plugin import AIPlugin
from .plugin_registry import AIPluginRegistry
from .orchestrator import AIAssistantOrchestrator
from .aggregator import SuggestionAggregator, AnalysisAggregator
from .resource_manager import AIResourceManager
from .service import AIAssistantService

__all__ = [
    "AIPlugin",
    "AIPluginRegistry",
    "AIAssistantOrchestrator",
    "SuggestionAggregator",
    "AnalysisAggregator",
    "AIResourceManager",
    "AIAssistantService"
]
