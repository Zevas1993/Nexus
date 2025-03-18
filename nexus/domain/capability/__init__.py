"""
Capability abstraction layer package for Nexus AI Assistant.

This package provides a unified interface for accessing different capabilities
across multiple providers, enabling seamless integration of various AI services.
"""

from .abstraction import CapabilityType, CapabilityProvider, CapabilityManager
from .service import CapabilityService

__all__ = ["CapabilityType", "CapabilityProvider", "CapabilityManager", "CapabilityService"]
