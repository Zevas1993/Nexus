"""
Demo script to showcase Nexus AI Coding Tools functionality.

This script demonstrates how to use the Tabnine code completion
and Codiga code analysis plugins.
"""
import asyncio
import os
import sys
import logging
from typing import Dict, Any

# Add the parent directory to sys.path so we can import the Nexus modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from nexus.domain.ai_assistant import AIAssistantService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AppContext:
    """Simple app context for the demo."""
    
    def __init__(self):
        self.config = {
            "ai_assistant": {
                "max_ram_mb": 1024,
                "max_cpu_percent": 50,
                "max_gpu_mb": 512
            }
        }

async def load_file(file_path: str) -> str:
    """Load a file and return its contents."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error loading file {file_path}: {e}")
        return ""

async def demo_code_completion(service: AIAssistantService, code: str, language: str, line: int, column: int) -> None:
    """Demonstrate code completion using the Tabnine plugin."""
    logger.info(f"Demonstrating code completion for {language} at line {line}, column {column}")
    
    code_context = {
        "code": code,
        "language": language,
        "line": line,
        "column": column,
        "filename": f"code_sample.{language}"
    }
    
    result = await service.get_code_suggestions(code_context)
    
    if result["status"] == "success":
        suggestions = result.get("suggestions", [])
        logger.info(f"Received {len(suggestions)} suggestions:")
        
        for i, suggestion in enumerate(suggestions[:3]):  # Show top 3 suggestions
            confidence = suggestion.get("confidence", 0) * 100
            source = suggestion.get("source", "unknown")
            text = suggestion.get("text", "").replace("\n", "\\n")[:50]  # Truncate for display
            
            logger.info(f"  [{i+1}] ({confidence:.1f}% confidence from {source}) {text}...")
    else:
        logger.error(f"Error getting suggestions: {result.get('message', 'Unknown error')}")

async def demo_code_analysis(service: AIAssistantService, code: str, filename: str) -> None:
    """Demonstrate code analysis using the Codiga plugin."""
    logger.info(f"Demonstrating code analysis for {filename}")
    
    result = await service.analyze_code(code, filename)
    
    if result["status"] == "success":
        issues = result.get("issues", {})
        total_issues = sum(len(issues_at_loc) for issues_at_loc in issues.values())
        
        logger.info(f"Analysis found {total_issues} issues in {filename}:")
        
        # Group issues by severity for better reporting
        by_severity = {"high": [], "medium": [], "low": []}
        
        for location, issues_at_loc in issues.items():
            for issue in issues_at_loc:
                severity = issue.get("severity", "medium")
                by_severity[severity].append(issue)
        
        # Report high severity issues first
        if by_severity["high"]:
            logger.info("HIGH SEVERITY ISSUES:")
            for issue in by_severity["high"]:
                logger.info(f"  Line {issue.get('line', '?')}: {issue.get('name', 'Unknown issue')} - {issue.get('message', '')}")
        
        # Report medium severity issues
        if by_severity["medium"]:
            logger.info("MEDIUM SEVERITY ISSUES:")
            for issue in by_severity["medium"][:3]:  # Show top 3 medium issues
                logger.info(f"  Line {issue.get('line', '?')}: {issue.get('name', 'Unknown issue')} - {issue.get('message', '')}")
            if len(by_severity["medium"]) > 3:
                logger.info(f"  ... and {len(by_severity['medium']) - 3} more medium severity issues")
        
        # Summarize low severity issues
        if by_severity["low"]:
            logger.info(f"LOW SEVERITY ISSUES: {len(by_severity['low'])} issues found")
            
    else:
        logger.error(f"Error analyzing code: {result.get('message', 'Unknown error')}")

async def main():
    """Main function to run the demo."""
    logger.info("Starting AI Coding Tools Demo")
    
    # Create app context and service
    app_context = AppContext()
    service = AIAssistantService(app_context)
    
    # Initialize service
    logger.info("Initializing AI Assistant Service")
    await service.initialize()
    
    # Get system resource information
    resources = await service.get_system_resources()
    logger.info(f"System resources: RAM {resources.get('ram_used_mb', '?')}MB / {resources.get('ram_total_mb', '?')}MB, CPU {resources.get('cpu_percent', '?')}%")
    
    # Load sample files
    js_code = await load_file(os.path.join(os.path.dirname(__file__), 'code_sample.js'))
    py_code = await load_file(os.path.join(os.path.dirname(__file__), 'code_sample.py'))
    
    # Demo 1: JavaScript code completion
    logger.info("\n=== JavaScript Code Completion Demo ===")
    # Complete a function body after 'function loadUserProfile() {'
    js_line = 57  # Line with function loadUserProfile()
    js_column = 33  # Position after the opening brace
    await demo_code_completion(service, js_code, "javascript", js_line, js_column)
    
    # Demo 2: Python code completion
    logger.info("\n=== Python Code Completion Demo ===")
    # Complete a function body after 'def calculate_average(numbers):'
    py_line = 75  # Line with def calculate_average(numbers):
    py_column = 32  # Position after the colon
    await demo_code_completion(service, py_code, "python", py_line, py_column)
    
    # Demo 3: JavaScript code analysis
    logger.info("\n=== JavaScript Code Analysis Demo ===")
    await demo_code_analysis(service, js_code, "code_sample.js")
    
    # Demo 4: Python code analysis
    logger.info("\n=== Python Code Analysis Demo ===")
    await demo_code_analysis(service, py_code, "code_sample.py")
    
    # Shutdown service
    logger.info("\nShutting down AI Assistant Service")
    await service.shutdown()
    
    logger.info("AI Coding Tools Demo completed")

if __name__ == "__main__":
    asyncio.run(main())
