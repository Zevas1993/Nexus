"""
Web scraping service for Nexus AI Assistant.

This module provides functionality for scraping web content.
"""

from typing import Dict, Any, Optional, List
import logging
import requests
from bs4 import BeautifulSoup
import urllib.parse
from ..base import AsyncService

logger = logging.getLogger(__name__)

class ScraperService(AsyncService):
    """Service for web scraping."""
    
    def __init__(self, app_context=None, config=None):
        """Initialize web scraper service.
        
        Args:
            app_context: Application context
            config: Configuration dictionary
        """
        super().__init__(app_context, config)
        self.user_agent = config.get('SCRAPER_USER_AGENT', 'Nexus AI Assistant/1.0')
        self.timeout = config.get('SCRAPER_TIMEOUT', 10)
        self.max_size = config.get('SCRAPER_MAX_SIZE', 1024 * 1024)  # 1MB
    
    async def _process_impl(self, request: str, **kwargs) -> Dict[str, Any]:
        """Implementation of request processing.
        
        Args:
            request: URL to scrape
            **kwargs: Additional parameters
                - selector: CSS selector to extract specific content
                - extract_links: Whether to extract links
                - extract_images: Whether to extract image URLs
                - extract_tables: Whether to extract tables
                
        Returns:
            Scraping result
        """
        url = request
        selector = kwargs.get('selector')
        extract_links = kwargs.get('extract_links', False)
        extract_images = kwargs.get('extract_images', False)
        extract_tables = kwargs.get('extract_tables', False)
        
        if not url.startswith(('http://', 'https://')):
            return {
                "status": "error",
                "message": "Invalid URL. Must start with http:// or https://"
            }
        
        try:
            # Fetch page content
            headers = {'User-Agent': self.user_agent}
            response = requests.get(url, headers=headers, timeout=self.timeout, 
                                   stream=True)
            response.raise_for_status()
            
            # Check content size
            content_length = int(response.headers.get('Content-Length', 0))
            if content_length > self.max_size:
                return {
                    "status": "error",
                    "message": f"Content too large: {content_length} bytes (max {self.max_size})"
                }
            
            # Read content with size limit
            content = b''
            for chunk in response.iter_content(chunk_size=8192):
                content += chunk
                if len(content) > self.max_size:
                    return {
                        "status": "error",
                        "message": f"Content too large (max {self.max_size} bytes)"
                    }
            
            # Parse HTML
            soup = BeautifulSoup(content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.extract()
            
            result = {
                "url": url,
                "title": soup.title.string if soup.title else None,
                "content_type": response.headers.get('Content-Type'),
                "status_code": response.status_code
            }
            
            # Extract specific content if selector provided
            if selector:
                selected_elements = soup.select(selector)
                result["selected_content"] = "\n".join(elem.get_text(strip=True) for elem in selected_elements)
                result["selected_html"] = "\n".join(str(elem) for elem in selected_elements)
                result["selected_count"] = len(selected_elements)
            
            # Extract main content
            main_content = soup.get_text(separator="\n", strip=True)
            result["content"] = main_content
            
            # Extract links if requested
            if extract_links:
                links = []
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    # Convert relative URLs to absolute
                    if not href.startswith(('http://', 'https://')):
                        href = urllib.parse.urljoin(url, href)
                    links.append({
                        "text": link.get_text(strip=True),
                        "url": href
                    })
                result["links"] = links
            
            # Extract images if requested
            if extract_images:
                images = []
                for img in soup.find_all('img', src=True):
                    src = img['src']
                    # Convert relative URLs to absolute
                    if not src.startswith(('http://', 'https://')):
                        src = urllib.parse.urljoin(url, src)
                    images.append({
                        "alt": img.get('alt', ''),
                        "url": src
                    })
                result["images"] = images
            
            # Extract tables if requested
            if extract_tables:
                tables = []
                for table in soup.find_all('table'):
                    table_data = []
                    rows = table.find_all('tr')
                    
                    # Extract headers
                    headers = []
                    header_row = table.find('thead')
                    if header_row:
                        for th in header_row.find_all(['th', 'td']):
                            headers.append(th.get_text(strip=True))
                    
                    # Extract rows
                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        if cells:
                            row_data = [cell.get_text(strip=True) for cell in cells]
                            table_data.append(row_data)
                    
                    tables.append({
                        "headers": headers,
                        "rows": table_data
                    })
                result["tables"] = tables
            
            return {
                "status": "success",
                "result": result
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching URL {url}: {str(e)}")
            return {
                "status": "error",
                "message": f"Error fetching URL: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Error scraping URL {url}: {str(e)}")
            return {
                "status": "error",
                "message": f"Error scraping URL: {str(e)}"
            }
