"""
Tabnine AI code completion plugin for Nexus.
"""
import os
import logging
import asyncio
import subprocess
import json
import re
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

class TabnineAssistant:
    """AI code completion using Tabnine."""
    
    def __init__(self, config=None):
        """Initialize Tabnine assistant.
        
        Args:
            config: Optional configuration
        """
        self.config = config or {}
        self.mode = "hybrid"  # Default to hybrid mode
        self.languages = ["python", "javascript"]
        self.suggestion_type = "inline"
        self.initialized = False
        self.tabnine_path = None
        self.local_model_loaded = False
        self.api_key = os.getenv("TABNINE_API_KEY", self.config.get("TABNINE_API_KEY", ""))
        
    async def initialize(self) -> bool:
        """Initialize the Tabnine client.
        
        Returns:
            True if initialization succeeded
        """
        try:
            # Find Tabnine binary or initialize API client
            result = subprocess.run(
                ["pip", "show", "tabnine"], 
                capture_output=True, 
                text=True
            )
            
            if result.returncode != 0:
                logger.error("Tabnine package not found")
                return False
                
            # In a full implementation, we would:
            # 1. Check for local model availability
            # 2. Download model if needed
            # 3. Initialize client
            
            # For now, we'll simulate successful initialization
            self.initialized = True
            
            # Simulate model initialization based on mode
            if self.mode == "local" or self.mode == "hybrid":
                logger.info("Initializing local Tabnine model")
                # Simulate local model loading delay
                await asyncio.sleep(0.5)
                self.local_model_loaded = True
                logger.info("Local Tabnine model loaded")
            
            logger.info("Tabnine assistant initialized")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing Tabnine: {str(e)}")
            return False
            
    async def process(self, request: str, **kwargs) -> Dict[str, Any]:
        """Process a code completion request.
        
        Args:
            request: Request string
            **kwargs: Additional parameters
                - plugin_inputs: Dictionary of plugin inputs
                - context: Current code context
            
        Returns:
            Code completion suggestions
        """
        if not self.initialized:
            success = await self.initialize()
            if not success:
                return {
                    "status": "error",
                    "message": "Tabnine initialization failed"
                }
                
        # Get plugin inputs and code context
        plugin_inputs = kwargs.get('plugin_inputs', {})
        context = kwargs.get('context', {})
        
        # Extract code context
        code = context.get('code', '')
        filename = context.get('filename', '')
        line = context.get('line', 0)
        column = context.get('column', 0)
        
        # Override defaults with plugin inputs
        mode = plugin_inputs.get('mode', self.mode)
        languages = plugin_inputs.get('languages', self.languages)
        suggestion_type = plugin_inputs.get('suggestion_type', self.suggestion_type)
        
        # Determine language based on filename or explicit language
        language = self._detect_language(filename, code, context.get('language'))
        
        # Check if we support this language
        if language and language not in languages:
            return {
                "status": "error",
                "message": f"Language {language} not enabled in plugin settings"
            }
            
        # Choose processing method based on mode and availability
        if mode == "local" or (mode == "hybrid" and self.local_model_loaded):
            suggestions = await self._process_local(code, line, column, language, suggestion_type)
        else:
            suggestions = await self._process_cloud(code, line, column, language, suggestion_type)
            
        return {
            "status": "success",
            "suggestions": suggestions,
            "position": {
                "line": line,
                "column": column
            },
            "language": language,
            "processing_mode": "local" if mode == "local" or (mode == "hybrid" and self.local_model_loaded) else "cloud"
        }
        
    async def _process_local(self, code: str, line: int, column: int, 
                          language: Optional[str], suggestion_type: str) -> List[Dict[str, Any]]:
        """Process using local model.
        
        Args:
            code: Source code
            line: Line number
            column: Column number
            language: Programming language
            suggestion_type: Type of suggestion
            
        Returns:
            List of suggestions
        """
        # In a full implementation, this would use the local Tabnine model
        # For now, we'll return mock suggestions
        
        # Extract context around the cursor
        context_before, context_after = self._extract_context(code, line, column)
        
        # Generate mock suggestions based on context
        suggestions = []
        
        # Based on what's before the cursor, generate appropriate suggestions
        if language == "python":
            if "def " in context_before:
                # Function definition context
                if suggestion_type == "full":
                    suggestions.append({
                        "text": "calculate_total(items):\n    return sum(item.price for item in items)",
                        "confidence": 0.92,
                        "metadata": {
                            "type": "function"
                        }
                    })
                    suggestions.append({
                        "text": "process_data(data):\n    result = []\n    for item in data:\n        result.append(item.transform())\n    return result",
                        "confidence": 0.85,
                        "metadata": {
                            "type": "function"
                        }
                    })
                else:
                    # Extract function name pattern
                    match = re.search(r"def\s+(\w+)\s*\(", context_before)
                    if match:
                        func_name = match.group(1)
                        if func_name.startswith("get_"):
                            suggestions.append({
                                "text": "item):\n    return self.items.get(item, None)",
                                "confidence": 0.9,
                                "metadata": {
                                    "type": "function_params"
                                }
                            })
                        elif func_name.startswith("calculate_"):
                            suggestions.append({
                                "text": "x, y):\n    return x + y",
                                "confidence": 0.85,
                                "metadata": {
                                    "type": "function_params"
                                }
                            })
                    else:
                        suggestions.append({
                            "text": "process_data(data):",
                            "confidence": 0.8,
                            "metadata": {
                                "type": "function_header"
                            }
                        })
            elif "class " in context_before:
                # Class definition context
                suggestions.append({
                    "text": "Result:\n    def __init__(self, value):\n        self.value = value",
                    "confidence": 0.9,
                    "metadata": {
                        "type": "class"
                    }
                })
            elif "if " in context_before:
                # Conditional context
                suggestions.append({
                    "text": "item.status == 'completed':",
                    "confidence": 0.85,
                    "metadata": {
                        "type": "condition"
                    }
                })
            elif "for " in context_before:
                # Loop context
                suggestions.append({
                    "text": "item in items:",
                    "confidence": 0.88,
                    "metadata": {
                        "type": "loop"
                    }
                })
            elif "import " in context_before:
                # Import context
                suggestions.append({
                    "text": "os",
                    "confidence": 0.95,
                    "metadata": {
                        "type": "import"
                    }
                })
                suggestions.append({
                    "text": "json",
                    "confidence": 0.9,
                    "metadata": {
                        "type": "import"
                    }
                })
            else:
                # Generic suggestions
                suggestions.append({
                    "text": "result = process_data(items)",
                    "confidence": 0.7,
                    "metadata": {
                        "type": "line"
                    }
                })
                suggestions.append({
                    "text": "for item in items:\n    print(item)",
                    "confidence": 0.65,
                    "metadata": {
                        "type": "block"
                    }
                })
        elif language == "javascript":
            if "function " in context_before:
                # Function context
                if suggestion_type == "full":
                    suggestions.append({
                        "text": "calculateTotal(items) {\n  return items.reduce((sum, item) => sum + item.price, 0);\n}",
                        "confidence": 0.9,
                        "metadata": {
                            "type": "function"
                        }
                    })
                else:
                    suggestions.append({
                        "text": "(data) {\n  return data.map(item => item.transform());\n}",
                        "confidence": 0.85,
                        "metadata": {
                            "type": "function_body"
                        }
                    })
            elif "const " in context_before or "let " in context_before:
                # Variable declarations
                suggestions.append({
                    "text": "result = await processData(items);",
                    "confidence": 0.88,
                    "metadata": {
                        "type": "variable"
                    }
                })
            elif "import " in context_before:
                # Import/require context
                suggestions.append({
                    "text": "{ useState, useEffect } from 'react';",
                    "confidence": 0.9,
                    "metadata": {
                        "type": "import"
                    }
                })
            else:
                # Generic JS suggestions
                suggestions.append({
                    "text": "const data = await fetch('/api/data');",
                    "confidence": 0.7,
                    "metadata": {
                        "type": "line"
                    }
                })
                suggestions.append({
                    "text": "if (condition) {\n  doSomething();\n}",
                    "confidence": 0.65,
                    "metadata": {
                        "type": "block"
                    }
                })
        
        # Fall back to generic suggestions if no language-specific ones
        if not suggestions:
            suggestions.append({
                "text": "// TODO: Implement this function",
                "confidence": 0.5,
                "metadata": {
                    "type": "comment"
                }
            })
            
        return suggestions
        
    async def _process_cloud(self, code: str, line: int, column: int, 
                          language: Optional[str], suggestion_type: str) -> List[Dict[str, Any]]:
        """Process using cloud API.
        
        Args:
            code: Source code
            line: Line number
            column: Column number
            language: Programming language
            suggestion_type: Type of suggestion
            
        Returns:
            List of suggestions
        """
        # In a full implementation, this would call the Tabnine Cloud API
        # For now, we'll return slightly different mock suggestions than the local version
        
        # Extract context around the cursor
        context_before, context_after = self._extract_context(code, line, column)
        
        # Generate cloud suggestions (slightly higher quality than local ones)
        # For demonstration, we'll just return similar but "better" suggestions
        local_suggestions = await self._process_local(code, line, column, language, suggestion_type)
        
        # Enhance the suggestions to simulate "better" cloud responses
        cloud_suggestions = []
        for suggestion in local_suggestions:
            # Deep copy the suggestion
            enhanced = {
                "text": suggestion["text"],
                "confidence": min(suggestion["confidence"] + 0.07, 0.99),  # Higher confidence
                "metadata": suggestion["metadata"].copy()
            }
            
            # Add more context or details to the suggestion text
            if suggestion["metadata"]["type"] == "function":
                # Add docstring or comments
                if language == "python":
                    if not enhanced["text"].startswith('"""'):
                        parts = enhanced["text"].split(":\n", 1)
                        if len(parts) > 1:
                            enhanced["text"] = f"{parts[0]}:\n    \"\"\"\n    Function documentation\n    \"\"\"\n    {parts[1]}"
                elif language == "javascript":
                    if not enhanced["text"].startswith("/**"):
                        parts = enhanced["text"].split("{", 1)
                        if len(parts) > 1:
                            enhanced["text"] = f"{parts[0]}{{\n  // Process and transform the data\n  {parts[1]}"
            
            cloud_suggestions.append(enhanced)
            
        # Add an extra cloud-specific suggestion
        if language == "python":
            cloud_suggestions.append({
                "text": "async with aiohttp.ClientSession() as session:\n    async with session.get(url) as response:\n        return await response.json()",
                "confidence": 0.92,
                "metadata": {
                    "type": "async_code"
                }
            })
        elif language == "javascript":
            cloud_suggestions.append({
                "text": "try {\n  const response = await fetch(url);\n  return await response.json();\n} catch (error) {\n  console.error('Error fetching data:', error);\n  throw error;\n}",
                "confidence": 0.94,
                "metadata": {
                    "type": "async_code"
                }
            })
            
        return cloud_suggestions
        
    def _extract_context(self, code: str, line: int, column: int) -> Tuple[str, str]:
        """Extract context before and after cursor.
        
        Args:
            code: Source code
            line: Line number (0-based)
            column: Column number (0-based)
            
        Returns:
            Tuple of (context_before, context_after)
        """
        if not code:
            return "", ""
            
        lines = code.split('\n')
        
        # Ensure valid line and column
        if line < 0 or line >= len(lines):
            line = max(0, min(line, len(lines) - 1))
        
        current_line = lines[line] if lines else ""
        
        if column < 0 or column > len(current_line):
            column = max(0, min(column, len(current_line)))
            
        # Extract context
        context_before = current_line[:column]
        context_after = current_line[column:]
        
        # Include a few previous lines for better context
        max_prev_lines = 3
        for i in range(max(0, line - max_prev_lines), line):
            context_before = lines[i] + "\n" + context_before
            
        return context_before, context_after
        
    def _detect_language(self, filename: str, code: str, explicit_language: Optional[str] = None) -> Optional[str]:
        """Detect programming language from filename or code.
        
        Args:
            filename: Name of the file
            code: Source code
            explicit_language: Explicitly specified language
            
        Returns:
            Detected language or None
        """
        # If language is explicitly specified, use that
        if explicit_language:
            return explicit_language.lower()
            
        # Detect from filename extension
        if filename:
            ext = os.path.splitext(filename)[1].lower()
            if ext in ('.py', '.pyw'):
                return "python"
            elif ext in ('.js', '.jsx'):
                return "javascript"
            elif ext in ('.ts', '.tsx'):
                return "typescript"
            elif ext in ('.html', '.htm'):
                return "html"
            elif ext in ('.css'):
                return "css"
                
        # Detect from code content (simplified)
        if code:
            # Check for Python patterns
            if re.search(r"import\s+[\w\.]+|def\s+\w+\s*\(|class\s+\w+\s*:", code):
                return "python"
            # Check for JavaScript patterns
            elif re.search(r"function\s+\w+\s*\(|const\s+\w+\s*=|let\s+\w+\s*=|var\s+\w+\s*=", code):
                return "javascript"
                
        # Default to Python if we can't detect
        return "python"
        
    def get_supported_roles(self) -> List[str]:
        """Get roles supported by this plugin.
        
        Returns:
            List of role identifiers
        """
        return ["COMPLETION"]
        
    def get_priority(self) -> int:
        """Get plugin priority (1-10).
        
        Returns:
            Priority value (higher is more important)
        """
        return 8
        
    def get_resource_requirements(self) -> Dict[str, Any]:
        """Get resource requirements.
        
        Returns:
            Dictionary with resource requirements
        """
        # Local model needs more resources
        if self.mode == "local":
            return {
                "ram_mb": 1024,  # 1 GB RAM
                "cpu_percent": 25,
                "gpu_mb": 512  # 512 MB GPU memory
            }
        elif self.mode == "hybrid":
            return {
                "ram_mb": 512,  # 512 MB RAM
                "cpu_percent": 15,
                "gpu_mb": 256  # 256 MB GPU memory
            }
        else:  # Cloud mode
            return {
                "ram_mb": 128,  # Minimal RAM for API calls
                "cpu_percent": 5,
                "gpu_mb": 0  # No GPU needed
            }
