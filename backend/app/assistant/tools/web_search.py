# backend/app/assistant/tools/web_search.py
from ._base_tool import BaseTool
# Ensure duckduckgo-search is installed (add to requirements.txt)
try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None # Handle missing dependency gracefully
    print("WARNING: duckduckgo-search library not found. WebSearchTool will be disabled.")
    print("Please install it: pip install duckduckgo-search")

import logging

logger = logging.getLogger(__name__)

class WebSearchTool(BaseTool):
    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        if DDGS is None:
            return "Web search tool (disabled due to missing 'duckduckgo-search' library)."
        return ("Searches the web for information using DuckDuckGo. Useful for finding recent information, "
                "news, or details not present in internal knowledge. Input should be the search query string.")

    def run(self, query: str, max_results=3) -> str:
        """Performs a web search and returns formatted results."""
        if DDGS is None:
            return "Error: Web search tool is disabled because the 'duckduckgo-search' library is not installed."

        logger.info(f"Performing web search for: '{query}'")
        if not query:
            return "Error: No search query provided."

        try:
            # Use context manager for DDGS
            with DDGS(timeout=10) as ddgs: # Add a timeout
                # Fetch text results
                results = list(ddgs.text(query, max_results=max_results))

            if not results:
                return f"No web search results found for '{query}'."

            # Format results clearly
            formatted_results = []
            formatted_results.append(f"Web search results for '{query}':\n")
            for i, result in enumerate(results):
                title = result.get('title', 'N/A')
                snippet = result.get('body', 'N/A')
                url = result.get('href', 'N/A')
                formatted_results.append(f"Result {i+1}:\n  Title: {title}\n  Snippet: {snippet}\n  URL: {url}\n---")

            return "\n".join(formatted_results)

        except Exception as e:
            logger.error(f"Error during web search for '{query}': {e}", exc_info=True)
            return f"An error occurred while searching the web: {e}"

# Example Usage (if run directly for testing)
# if __name__ == '__main__':
#     if DDGS:
#         search_tool = WebSearchTool()
#         test_query = "latest news on AI advancements"
#         search_result = search_tool.run(test_query)
#         print(search_result)
#     else:
#         print("Cannot run example: duckduckgo-search not installed.")
