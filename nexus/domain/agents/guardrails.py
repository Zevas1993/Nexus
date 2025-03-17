"""
Guardrails for Nexus AI Agents based on OpenAI's Agents SDK.

This module provides validation mechanisms that ensure the integrity
and safety of inputs to agents, maintaining reliability in operations.
"""
import logging
import re
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple, Pattern, Set, Union

logger = logging.getLogger(__name__)

class Guardrail(ABC):
    """Base class for agent guardrails."""
    
    def __init__(self, name: str, description: str):
        """Initialize a guardrail.
        
        Args:
            name: Guardrail name
            description: Guardrail description
        """
        self.name = name
        self.description = description
        logger.info(f"Guardrail '{name}' initialized")
        
    @abstractmethod
    def validate(self, input_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate input data against the guardrail.
        
        Args:
            input_data: Input data to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        pass

class ContentFilterGuardrail(Guardrail):
    """Guardrail for filtering harmful or inappropriate content."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize content filter guardrail.
        
        Args:
            config: Configuration options
        """
        super().__init__(
            name="content_filter",
            description="Filter harmful or inappropriate content"
        )
        self.config = config or {}
        self.blocked_patterns: List[Pattern] = []
        
        # Initialize blocked patterns
        blocked_terms = self.config.get("BLOCKED_TERMS", [
            "harmful instructions",
            "illegal activity",
            "violence",
            "explicit content"
        ])
        
        for term in blocked_terms:
            try:
                pattern = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
                self.blocked_patterns.append(pattern)
            except re.error:
                logger.warning(f"Invalid regex pattern for term: {term}")
        
    def validate(self, input_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate input data for harmful content.
        
        Args:
            input_data: Input data to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Extract text from the input data
        text = ""
        
        # Handle different input formats
        if isinstance(input_data, dict):
            if "text" in input_data:
                text = input_data["text"]
            elif "task" in input_data:
                text = input_data["task"]
            elif "prompt" in input_data:
                text = input_data["prompt"]
        elif isinstance(input_data, str):
            text = input_data
            
        if not text:
            return True, None
            
        # Check for blocked patterns
        for pattern in self.blocked_patterns:
            match = pattern.search(text)
            if match:
                matched_term = match.group(0)
                logger.warning(f"Content filter blocked text containing: {matched_term}")
                return False, f"Content filter detected potentially harmful content: {matched_term}"
                
        return True, None

class DataValidationGuardrail(Guardrail):
    """Guardrail for validating data format and structure."""
    
    def __init__(self, schema: Dict[str, Any], config: Optional[Dict[str, Any]] = None):
        """Initialize data validation guardrail.
        
        Args:
            schema: JSON schema for validation
            config: Configuration options
        """
        super().__init__(
            name="data_validation",
            description="Validate data format and structure"
        )
        self.schema = schema
        self.config = config or {}
        
    def validate(self, input_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate input data against JSON schema.
        
        Args:
            input_data: Input data to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # In a real implementation, this would use jsonschema or similar
            # For now, we'll do a basic check
            
            # Check required fields
            if "required" in self.schema:
                for field in self.schema["required"]:
                    if field not in input_data:
                        return False, f"Missing required field: {field}"
            
            # Check data types
            if "properties" in self.schema:
                for field, field_schema in self.schema["properties"].items():
                    if field in input_data:
                        field_type = field_schema.get("type")
                        
                        if field_type == "string" and not isinstance(input_data[field], str):
                            return False, f"Field '{field}' must be a string"
                        elif field_type == "number" and not isinstance(input_data[field], (int, float)):
                            return False, f"Field '{field}' must be a number"
                        elif field_type == "integer" and not isinstance(input_data[field], int):
                            return False, f"Field '{field}' must be an integer"
                        elif field_type == "boolean" and not isinstance(input_data[field], bool):
                            return False, f"Field '{field}' must be a boolean"
                        elif field_type == "array" and not isinstance(input_data[field], list):
                            return False, f"Field '{field}' must be an array"
                        elif field_type == "object" and not isinstance(input_data[field], dict):
                            return False, f"Field '{field}' must be an object"
            
            return True, None
        except Exception as e:
            logger.error(f"Error validating data: {str(e)}")
            return False, f"Data validation error: {str(e)}"

class RateLimitGuardrail(Guardrail):
    """Guardrail for enforcing rate limits."""
    
    def __init__(self, limits: Dict[str, int], config: Optional[Dict[str, Any]] = None):
        """Initialize rate limit guardrail.
        
        Args:
            limits: Dictionary of rate limits (e.g., {"user_id": 10})
            config: Configuration options
        """
        super().__init__(
            name="rate_limit",
            description="Enforce rate limits"
        )
        self.limits = limits
        self.config = config or {}
        self.counters: Dict[str, Dict[str, int]] = {}
        
    def validate(self, input_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate input data against rate limits.
        
        Args:
            input_data: Input data to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check each rate limit
        for key, limit in self.limits.items():
            # Extract the identifier from input data
            identifier = None
            
            if key in input_data:
                identifier = input_data[key]
            elif key == "user_id" and "user" in input_data:
                identifier = input_data["user"]
            elif key == "ip_address" and "request" in input_data and "remote_addr" in input_data["request"]:
                identifier = input_data["request"]["remote_addr"]
                
            if identifier:
                # Initialize counter if not exists
                if key not in self.counters:
                    self.counters[key] = {}
                    
                if identifier not in self.counters[key]:
                    self.counters[key][identifier] = 0
                    
                # Increment counter
                self.counters[key][identifier] += 1
                
                # Check if over limit
                if self.counters[key][identifier] > limit:
                    logger.warning(f"Rate limit exceeded for {key}={identifier}: {self.counters[key][identifier]} > {limit}")
                    return False, f"Rate limit exceeded for {key}"
        
        return True, None
        
    def reset_counters(self):
        """Reset all rate limit counters."""
        self.counters = {}
        
    def reset_counter(self, key: str, identifier: str):
        """Reset a specific rate limit counter.
        
        Args:
            key: Counter key
            identifier: Counter identifier
        """
        if key in self.counters and identifier in self.counters[key]:
            self.counters[key][identifier] = 0

class CompositeGuardrail(Guardrail):
    """Guardrail that combines multiple other guardrails."""
    
    def __init__(self, guardrails: List[Guardrail], config: Optional[Dict[str, Any]] = None):
        """Initialize composite guardrail.
        
        Args:
            guardrails: List of guardrails to combine
            config: Configuration options
        """
        super().__init__(
            name="composite_guardrail",
            description="Combines multiple guardrails"
        )
        self.guardrails = guardrails
        self.config = config or {}
        
    def validate(self, input_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate input data against all guardrails.
        
        Args:
            input_data: Input data to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        for guardrail in self.guardrails:
            is_valid, error = guardrail.validate(input_data)
            if not is_valid:
                return False, error
                
        return True, None
