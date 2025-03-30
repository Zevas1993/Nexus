# backend/app/assistant/tools/__init__.py
from .calculator import CalculatorTool
from .web_search import WebSearchTool
import logging

logger = logging.getLogger(__name__)

# Simple dictionary-based registry
# Instantiate tools here
_tools = {}
try:
    _tools["calculator"] = CalculatorTool()
    _tools["web_search"] = WebSearchTool()
    # Add more tools here as they are created
    logger.info(f"Initialized tools: {list(_tools.keys())}")
except Exception as e:
    logger.error(f"Failed to initialize one or more tools: {e}", exc_info=True)


def get_tool(name: str):
    """Retrieves an instantiated tool by name."""
    tool = _tools.get(name)
    if not tool:
        logger.warning(f"Attempted to retrieve non-existent tool: {name}")
    return tool

def get_available_tools_list():
    """Returns a list of available tool names."""
    return list(_tools.keys())

def get_tool_descriptions():
    """Returns a formatted string of tool names and descriptions."""
    if not _tools:
        return "No tools available."
    return "\n".join([f"- {name}: {tool.description}" for name, tool in _tools.items() if hasattr(tool, 'description')])
