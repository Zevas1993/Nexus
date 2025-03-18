"""
Codiga code analysis plugin for Nexus.
"""
import os
import logging
import re
import json
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

class CodigaAnalyzer:
    """Code quality and security analysis using Codiga."""
    
    def __init__(self, config=None):
        """Initialize Codiga analyzer.
        
        Args:
            config: Optional configuration
        """
        self.config = config or {}
        self.analysis_level = "standard"
        self.categories = ["security", "performance", "maintainability"]
        self.rulesets = ["python-security", "javascript-security"]
        self.initialized = False
        self.api_key = os.getenv("CODIGA_API_KEY", self.config.get("CODIGA_API_KEY", ""))
        
        # Rule definitions would normally be loaded from Codiga
        # Here we'll include a small set of mock rules for demonstration
        self._load_rules()
        
    async def initialize(self) -> bool:
        """Initialize the Codiga client.
        
        Returns:
            True if initialization succeeded
        """
        try:
            # In a real implementation, we would initialize the Codiga client
            # and validate API credentials
            
            # For now, we'll simulate successful initialization
            self.initialized = True
            logger.info("Codiga analyzer initialized")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing Codiga: {str(e)}")
            return False
            
    def _load_rules(self) -> None:
        """Load rule definitions."""
        # In a real implementation, these would be loaded from Codiga's API
        # or from local rule definition files
        
        self.rules = {
            "python": {
                "security": [
                    {
                        "id": "python-sql-injection",
                        "name": "SQL Injection Vulnerability",
                        "pattern": r"execute\(\s*[\"']SELECT.*\%s.*[\"']",
                        "message": "Possible SQL injection vulnerability. Use parameterized queries with placeholders.",
                        "severity": "high",
                        "category": "security"
                    },
                    {
                        "id": "python-os-command-injection",
                        "name": "OS Command Injection",
                        "pattern": r"os\.system\(.*\+.*\)|subprocess\.call\(.*\+.*\)",
                        "message": "Possible command injection. Avoid using dynamic strings in command execution.",
                        "severity": "high",
                        "category": "security"
                    },
                    {
                        "id": "python-insecure-deserialization",
                        "name": "Insecure Deserialization",
                        "pattern": r"pickle\.loads\(|yaml\.load\([^)]+\)",
                        "message": "Insecure deserialization could lead to remote code execution. Use pickle.loads with trusted data only or yaml.safe_load().",
                        "severity": "high",
                        "category": "security"
                    }
                ],
                "performance": [
                    {
                        "id": "python-inefficient-list-comp",
                        "name": "Inefficient List Operation",
                        "pattern": r"for\s+\w+\s+in\s+.*:\s*\w+\.append\(",
                        "message": "Consider using a list comprehension for better performance.",
                        "severity": "medium",
                        "category": "performance"
                    },
                    {
                        "id": "python-repeated-calculation",
                        "name": "Repeated Calculation in Loop",
                        "pattern": r"for.*in.*:.*\w+\.\w+\(\).*\w+\.\w+\(\)",
                        "message": "Possible repeated calculation in loop. Consider storing the result of the method call outside the loop.",
                        "severity": "medium",
                        "category": "performance"
                    }
                ],
                "maintainability": [
                    {
                        "id": "python-too-many-arguments",
                        "name": "Too Many Function Arguments",
                        "pattern": r"def\s+\w+\s*\([^)]{80,}\):",
                        "message": "Function has too many arguments. Consider refactoring using a class or data structure.",
                        "severity": "medium",
                        "category": "maintainability"
                    },
                    {
                        "id": "python-nested-loops",
                        "name": "Deeply Nested Loops",
                        "pattern": r"for.*:.*for.*:.*for.*:",
                        "message": "Deeply nested loops detected. Consider refactoring for readability and maintainability.",
                        "severity": "medium",
                        "category": "maintainability"
                    }
                ],
                "style": [
                    {
                        "id": "python-unused-import",
                        "name": "Possibly Unused Import",
                        "pattern": r"import\s+(\w+)",
                        "special": "check_unused_import",
                        "message": "Import may be unused in this file.",
                        "severity": "low",
                        "category": "style"
                    },
                    {
                        "id": "python-line-length",
                        "name": "Line Too Long",
                        "pattern": r".{100,}",
                        "message": "Line length exceeds recommended maximum of 100 characters.",
                        "severity": "low",
                        "category": "style"
                    }
                ]
            },
            "javascript": {
                "security": [
                    {
                        "id": "js-xss",
                        "name": "Cross-Site Scripting (XSS)",
                        "pattern": r"innerHTML\s*=|document\.write\(",
                        "message": "Potential XSS vulnerability. Consider using textContent or sanitize input.",
                        "severity": "high",
                        "category": "security"
                    },
                    {
                        "id": "js-eval-usage",
                        "name": "Use of eval()",
                        "pattern": r"eval\(|new\s+Function\(",
                        "message": "Use of eval() or new Function() is dangerous and can lead to code injection.",
                        "severity": "high",
                        "category": "security"
                    }
                ],
                "performance": [
                    {
                        "id": "js-inefficient-dom-query",
                        "name": "Inefficient DOM Query",
                        "pattern": r"getElementsBy\w+\([^)]+\)|\$\([^)]+\)",
                        "message": "DOM query in a loop can cause performance issues. Consider caching the result outside the loop.",
                        "severity": "medium",
                        "category": "performance"
                    },
                    {
                        "id": "js-array-concat-in-loop",
                        "name": "Array Concatenation in Loop",
                        "pattern": r"for.*{.*\.concat\(",
                        "message": "Array concatenation in a loop is inefficient. Consider using push() or a different approach.",
                        "severity": "medium",
                        "category": "performance"
                    }
                ],
                "maintainability": [
                    {
                        "id": "js-complex-function",
                        "name": "Complex Function",
                        "pattern": r"function\s+\w+\s*\([^)]*\)\s*{(\s|.)*?return[^}]*}",
                        "special": "check_function_length",
                        "message": "Function is too complex. Consider refactoring into smaller functions.",
                        "severity": "medium",
                        "category": "maintainability"
                    },
                    {
                        "id": "js-nested-callbacks",
                        "name": "Nested Callbacks",
                        "pattern": r"function\s*\([^)]*\)\s*{.*function\s*\([^)]*\)\s*{.*function\s*\([^)]*\)",
                        "message": "Deeply nested callbacks detected. Consider using Promises or async/await.",
                        "severity": "medium",
                        "category": "maintainability"
                    }
                ],
                "style": [
                    {
                        "id": "js-inconsistent-quotes",
                        "name": "Inconsistent String Quotes",
                        "pattern": r"'[^']*'|\"[^\"]*\"",
                        "special": "check_mixed_quotes",
                        "message": "Mix of single and double quotes detected. Consider using one style consistently.",
                        "severity": "low",
                        "category": "style"
                    },
                    {
                        "id": "js-trailing-comma",
                        "name": "Missing Trailing Comma",
                        "pattern": r"{[^}]*,[^}]*}|\\[[^\\]]*,[^\\]]*\\]",
                        "special": "check_trailing_comma",
                        "message": "Consider using trailing commas in multiline object and array literals.",
                        "severity": "low",
                        "category": "style"
                    }
                ]
            }
        }
            
    async def process(self, request: str, **kwargs) -> Dict[str, Any]:
        """Process a code analysis request.
        
        Args:
            request: Request string
            **kwargs: Additional parameters
                - plugin_inputs: Dictionary of plugin inputs
                - context: Code context
            
        Returns:
            Analysis results with issues found
        """
        if not self.initialized:
            success = await self.initialize()
            if not success:
                return {
                    "status": "error",
                    "message": "Codiga analyzer initialization failed"
                }
                
        # Get plugin inputs and code context
        plugin_inputs = kwargs.get('plugin_inputs', {})
        context = kwargs.get('context', {})
        
        # Extract code context
        code = context.get('code', '')
        filename = context.get('filename', '')
        
        if not code:
            return {
                "status": "error",
                "message": "No code provided for analysis"
            }
            
        # Override defaults with plugin inputs
        analysis_level = plugin_inputs.get('analysis_level', self.analysis_level)
        categories = plugin_inputs.get('categories', self.categories)
        rulesets = plugin_inputs.get('rulesets', self.rulesets)
        
        # Determine language from filename or try to detect
        language = self._detect_language(filename, code)
        if not language:
            return {
                "status": "error",
                "message": "Could not detect language for analysis"
            }
            
        # Check if we have rules for this language
        if language not in self.rules:
            return {
                "status": "error",
                "message": f"No rules available for language: {language}"
            }
            
        # Select appropriate rules based on categories and rulesets
        selected_rules = []
        for category in categories:
            if category in self.rules[language]:
                category_rules = self.rules[language][category]
                
                # Filter by ruleset if applicable
                if rulesets:
                    # In a real implementation, we would filter by ruleset
                    # Here we'll include all rules for the selected categories
                    pass
                    
                selected_rules.extend(category_rules)
                
        # Apply the analysis with the selected level and rules
        issues = await self._analyze_code(code, language, selected_rules, analysis_level)
        
        return {
            "status": "success",
            "language": language,
            "issues": issues,
            "summary": {
                "total_issues": len(issues),
                "by_severity": self._count_issues_by_severity(issues),
                "by_category": self._count_issues_by_category(issues)
            }
        }
        
    async def _analyze_code(self, code: str, language: str, 
                           rules: List[Dict[str, Any]], level: str) -> List[Dict[str, Any]]:
        """Analyze code with the selected rules and level.
        
        Args:
            code: Source code
            language: Programming language
            rules: List of rules to apply
            level: Analysis level (quick, standard, deep)
            
        Returns:
            List of issues found
        """
        issues = []
        
        # In a real implementation, we would call the Codiga API
        # For now, we'll perform a simple pattern-based analysis
        
        lines = code.split('\n')
        
        for rule in rules:
            # Apply the rule to the code
            pattern = rule.get('pattern', '')
            
            if not pattern:
                continue
                
            # Adjust rule behavior based on analysis level
            if level == "quick" and rule.get('severity') != "high":
                # Quick analysis only looks for high severity issues
                continue
                
            if level == "standard" and rule.get('severity') == "low" and rule.get('category') == "style":
                # Standard analysis skips low-priority style issues
                continue
                
            # Check for special rule handling
            special = rule.get('special', '')
            if special:
                # In a real implementation, we would handle special rules with custom logic
                # For now, we'll just use regular expression matching
                pass
                
            # Apply the pattern to each line
            for i, line in enumerate(lines):
                if re.search(pattern, line):
                    # Found an issue
                    issues.append({
                        "rule_id": rule.get('id', ''),
                        "name": rule.get('name', ''),
                        "message": rule.get('message', ''),
                        "severity": rule.get('severity', 'medium'),
                        "category": rule.get('category', ''),
                        "line": i,
                        "column": 0,  # In a real implementation, we would calculate the exact column
                        "snippet": line.strip()
                    })
                    
                    # If we're doing a quick analysis, limit the number of issues per rule
                    if level == "quick" and sum(1 for issue in issues if issue['rule_id'] == rule['id']) >= 3:
                        break
                        
        # Sort issues by severity and line number
        issues.sort(key=lambda x: (
            0 if x['severity'] == 'high' else 1 if x['severity'] == 'medium' else 2,
            x['line']
        ))
        
        return issues
        
    def _detect_language(self, filename: str, code: str) -> Optional[str]:
        """Detect programming language from filename or code.
        
        Args:
            filename: Name of the file
            code: Source code
            
        Returns:
            Detected language or None
        """
        # Detect from filename extension
        if filename:
            ext = os.path.splitext(filename)[1].lower()
            if ext in ('.py', '.pyw'):
                return "python"
            elif ext in ('.js', '.jsx'):
                return "javascript"
            elif ext in ('.ts', '.tsx'):
                return "typescript"  # We'll treat TypeScript as JavaScript for now
                
        # Detect from code content (simplified)
        if code:
            # Check for Python patterns
            if re.search(r"import\s+[\w\.]+|def\s+\w+\s*\(|class\s+\w+\s*:", code):
                return "python"
            # Check for JavaScript patterns
            elif re.search(r"function\s+\w+\s*\(|const\s+\w+\s*=|let\s+\w+\s*=|var\s+\w+\s*=", code):
                return "javascript"
                
        return None
        
    def _count_issues_by_severity(self, issues: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count issues by severity.
        
        Args:
            issues: List of issues
            
        Returns:
            Dictionary with counts by severity
        """
        counts = {"high": 0, "medium": 0, "low": 0}
        
        for issue in issues:
            severity = issue.get('severity', '')
            if severity in counts:
                counts[severity] += 1
                
        return counts
        
    def _count_issues_by_category(self, issues: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count issues by category.
        
        Args:
            issues: List of issues
            
        Returns:
            Dictionary with counts by category
        """
        counts = {}
        
        for issue in issues:
            category = issue.get('category', '')
            if category:
                counts[category] = counts.get(category, 0) + 1
                
        return counts
        
    def get_supported_roles(self) -> List[str]:
        """Get roles supported by this plugin.
        
        Returns:
            List of role identifiers
        """
        return ["ANALYSIS"]
        
    def get_priority(self) -> int:
        """Get plugin priority (1-10).
        
        Returns:
            Priority value (higher is more important)
        """
        return 7
        
    def get_resource_requirements(self) -> Dict[str, Any]:
        """Get resource requirements.
        
        Returns:
            Dictionary with resource requirements
        """
        return {
            "ram_mb": 128,  # Minimal RAM needed
            "cpu_percent": 10,
            "gpu_mb": 0  # No GPU needed
        }
