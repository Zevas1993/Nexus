"""
Plugin manifest handling for Nexus AI Assistant.

This module provides functionality for parsing and validating plugin manifests.
"""

from typing import Dict, Any, List, Optional, Union
import logging
import json
import os
import jsonschema

logger = logging.getLogger(__name__)

# JSON Schema for plugin manifest validation
MANIFEST_SCHEMA = {
    "type": "object",
    "required": ["name", "version", "class"],
    "properties": {
        "name": {"type": "string"},
        "version": {"type": "string"},
        "class": {"type": "string"},
        "dependencies": {
            "type": "array",
            "items": {"type": "string"}
        },
        "description": {"type": "string"},
        "default_prompt": {"type": "string"},
        "inputs": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "type", "label"],
                "properties": {
                    "id": {"type": "string"},
                    "type": {"type": "string", "enum": ["text", "select", "number", "boolean"]},
                    "label": {"type": "string"},
                    "default": {},
                    "options": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["value", "label"],
                            "properties": {
                                "value": {},
                                "label": {"type": "string"}
                            }
                        }
                    }
                }
            }
        }
    }
}

class PluginManifest:
    """Plugin manifest class."""
    
    def __init__(self, manifest_data: Dict[str, Any]):
        """Initialize plugin manifest.
        
        Args:
            manifest_data: Manifest data dictionary
        """
        self.data = manifest_data
        self.name = manifest_data["name"]
        self.version = manifest_data["version"]
        self.class_name = manifest_data["class"]
        self.dependencies = manifest_data.get("dependencies", [])
        self.description = manifest_data.get("description", f"{self.name} plugin")
        self.default_prompt = manifest_data.get("default_prompt", f"Use {self.name} plugin")
        self.inputs = manifest_data.get("inputs", [])
    
    @classmethod
    def from_file(cls, file_path: str) -> 'PluginManifest':
        """Load manifest from file.
        
        Args:
            file_path: Path to manifest file
            
        Returns:
            PluginManifest instance
            
        Raises:
            ValueError: If manifest is invalid
        """
        try:
            with open(file_path, 'r') as f:
                manifest_data = json.load(f)
            
            # Validate manifest
            jsonschema.validate(manifest_data, MANIFEST_SCHEMA)
            
            return cls(manifest_data)
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing manifest file {file_path}: {str(e)}")
            raise ValueError(f"Invalid JSON in manifest file: {str(e)}")
        except jsonschema.exceptions.ValidationError as e:
            logger.error(f"Invalid manifest file {file_path}: {str(e)}")
            raise ValueError(f"Invalid manifest format: {str(e)}")
        except Exception as e:
            logger.error(f"Error loading manifest file {file_path}: {str(e)}")
            raise ValueError(f"Error loading manifest: {str(e)}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert manifest to dictionary.
        
        Returns:
            Dictionary representation of manifest
        """
        return self.data.copy()
    
    def validate_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate input data against manifest inputs.
        
        Args:
            input_data: Input data dictionary
            
        Returns:
            Validated and processed input data
            
        Raises:
            ValueError: If input data is invalid
        """
        result = {}
        
        # Check for required inputs
        for input_def in self.inputs:
            input_id = input_def["id"]
            input_type = input_def["type"]
            
            # Check if input is provided
            if input_id not in input_data:
                # Use default if available
                if "default" in input_def:
                    result[input_id] = input_def["default"]
                    continue
                else:
                    raise ValueError(f"Missing required input: {input_id}")
            
            value = input_data[input_id]
            
            # Validate input type
            if input_type == "text":
                if not isinstance(value, str):
                    raise ValueError(f"Input {input_id} must be a string")
                result[input_id] = value
            elif input_type == "number":
                try:
                    result[input_id] = float(value)
                except (ValueError, TypeError):
                    raise ValueError(f"Input {input_id} must be a number")
            elif input_type == "boolean":
                if isinstance(value, bool):
                    result[input_id] = value
                elif isinstance(value, str):
                    result[input_id] = value.lower() in ('true', 'yes', '1')
                else:
                    raise ValueError(f"Input {input_id} must be a boolean")
            elif input_type == "select":
                # Validate against options
                options = input_def.get("options", [])
                valid_values = [opt["value"] for opt in options]
                if value not in valid_values:
                    raise ValueError(f"Input {input_id} must be one of: {', '.join(str(v) for v in valid_values)}")
                result[input_id] = value
        
        return result
