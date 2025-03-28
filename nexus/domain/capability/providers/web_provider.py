"""
Web Browsing Provider for Nexus AI Assistant.

This module provides capability providers for web browsing and data extraction
using headless browsers and web scraping tools.
"""
import logging
import json
import aiohttp
import os
import asyncio
import re
import html # <-- ADD THIS IMPORT
from typing import Dict, Any, List, Optional, Union
from urllib.parse import urlparse

# Import BeautifulSoup
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None
    logging.warning("BeautifulSoup4 not installed. Text extraction from HTML will be basic.")

from ..abstraction import CapabilityProvider, CapabilityType

logger = logging.getLogger(__name__)

class BrowserlessProvider(CapabilityProvider):
    """Browserless.io provider for web browsing capabilities."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize Browserless provider."""
        super().__init__("browserless", config)
        self.api_key = self.config.get("api_key", os.environ.get("BROWSERLESS_API_KEY", ""))
        self.api_url = self.config.get("api_url", "https://chrome.browserless.io")
        self.timeout = self.config.get("timeout", 60)
        self.max_wait = self.config.get("max_wait", 30000)  # 30 seconds
        self.default_user_agent = self.config.get(
            "user_agent",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )

    async def initialize(self) -> None:
        """Initialize the provider."""
        if not self.api_key:
            logger.warning("Browserless API key not provided, provider will be disabled")
            self.enabled = False
            return

        self.register_capability(CapabilityType.WEB_BROWSING, self.browse_url)

        # Test connection
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Cache-Control": "no-cache", "Content-Type": "application/json"} # Ensure content type
                params = {"token": self.api_key}
                test_payload = json.dumps({"url": "https://example.com", "waitFor": 1000})

                async with session.post( # Use POST for /content with payload
                    f"{self.api_url}/content",
                    headers=headers,
                    params=params,
                    timeout=10,
                    data=test_payload
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.warning(f"Browserless API test failed ({response.status}): {error_text}")
                        self.enabled = False
                    else:
                        logger.info("Browserless API connection successful")
        except Exception as e:
            logger.warning(f"Error connecting to Browserless API: {str(e)}")
            self.enabled = False

    async def browse_url(self,
                      url: str,
                      extract_text: bool = True,
                      take_screenshot: bool = False,
                      evaluate_script: Optional[str] = None,
                      wait_for_selector: Optional[str] = None,
                      wait_for_time: Optional[int] = None,
                      user_agent: Optional[str] = None,
                      **kwargs) -> Dict[str, Any]:
        """Browse a URL and extract content."""
        if not self.enabled:
            raise RuntimeError("Browserless provider is not enabled or failed initialization.")

        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise ValueError(f"Invalid URL: {url}")

        result = {
            "url": url, "title": "", "content": "", "screenshot": None,
            "script_result": None, "status": "error", "error": None
        }
        user_agent_to_use = user_agent or self.default_user_agent
        # Determine effective wait time
        effective_wait = wait_for_time if wait_for_time is not None else (self.max_wait if wait_for_selector else 5000)

        # --- Shared Payload Elements ---
        base_payload = {
            "url": url,
            "waitFor": effective_wait,
            "userAgent": user_agent_to_use
        }
        if wait_for_selector:
            base_payload["waitForSelector"] = wait_for_selector

        # --- Async Operations ---
        tasks = []
        content_task = None
        screenshot_task = None
        script_task = None

        async with aiohttp.ClientSession() as session:
            headers = {"Cache-Control": "no-cache", "Content-Type": "application/json"}
            params = {"token": self.api_key}

            # Create Content Task
            if extract_text:
                content_payload = base_payload.copy()
                content_task = asyncio.create_task(
                    session.post(f"{self.api_url}/content", headers=headers, params=params, json=content_payload, timeout=self.timeout)
                )
                tasks.append(content_task)

            # Create Screenshot Task
            if take_screenshot:
                screenshot_payload = base_payload.copy()
                screenshot_payload["options"] = {"fullPage": True, "type": "jpeg", "quality": 80}
                screenshot_task = asyncio.create_task(
                    session.post(f"{self.api_url}/screenshot", headers=headers, params=params, json=screenshot_payload, timeout=self.timeout)
                )
                tasks.append(screenshot_task)

            # Create Script Task
            if evaluate_script:
                script_payload = base_payload.copy()
                script_payload["code"] = evaluate_script
                script_task = asyncio.create_task(
                    session.post(f"{self.api_url}/function", headers=headers, params=params, json=script_payload, timeout=self.timeout)
                )
                tasks.append(script_task)

            # --- Wait for and Process Results ---
            results_gathered = await asyncio.gather(*tasks, return_exceptions=True)
            # Map results back to tasks for easier processing
            results_map = dict(zip([t for t in [content_task, screenshot_task, script_task] if t], results_gathered))


            # Process Content Result
            if content_task in results_map:
                content_res = results_map[content_task]
                if isinstance(content_res, Exception):
                    logger.error(f"Error retrieving content from {url}: {content_res}")
                    result["error"] = f"Error retrieving content: {content_res}"
                else:
                    try:
                        content_res.raise_for_status() # Raise exception for bad status codes
                        html_content = await content_res.text()
                        result["title"] = self._extract_title(html_content)
                        result["content"] = self._extract_text_from_html(html_content)
                        result["status"] = "success" # Mark success if at least content retrieval worked
                    except Exception as e:
                         logger.error(f"Error processing content response from {url}: {e}")
                         result["error"] = f"Error processing content response: {e}"


            # Process Screenshot Result
            if screenshot_task in results_map:
                 screenshot_res = results_map[screenshot_task]
                 if isinstance(screenshot_res, Exception):
                     logger.error(f"Error taking screenshot of {url}: {screenshot_res}")
                     if not result["error"]: result["error"] = f"Error taking screenshot: {screenshot_res}"
                 else:
                     try:
                         screenshot_res.raise_for_status()
                         result["screenshot"] = await screenshot_res.read()
                         if result["status"] != "success": result["status"] = "success" # Mark success if screenshot worked
                     except Exception as e:
                         logger.error(f"Error processing screenshot response from {url}: {e}")
                         if not result["error"]: result["error"] = f"Error processing screenshot response: {e}"


            # Process Script Result
            if script_task in results_map:
                 script_res = results_map[script_task]
                 if isinstance(script_res, Exception):
                     logger.error(f"Error evaluating script on {url}: {script_res}")
                     if not result["error"]: result["error"] = f"Error evaluating script: {script_res}"
                 else:
                     try:
                         script_res.raise_for_status()
                         result["script_result"] = await script_res.json() # Browserless /function returns JSON
                         if result["status"] != "success": result["status"] = "success"
                     except Exception as e:
                         logger.error(f"Error processing script response from {url}: {e}")
                         if not result["error"]: result["error"] = f"Error processing script response: {e}"

        return result

    def _extract_title(self, html: str) -> str:
        """Extract title using BeautifulSoup if available."""
        if BeautifulSoup:
            try:
                soup = BeautifulSoup(html, 'lxml') # Use lxml parser
                title_tag = soup.find('title')
                return title_tag.string.strip() if title_tag else ""
            except Exception as e:
                logger.warning(f"BeautifulSoup failed to extract title: {e}. Falling back to regex.")
        # Fallback regex
        title_match = re.search(r"<title.*?>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        return title_match.group(1).strip() if title_match else ""


    def _extract_text_from_html(self, html: str) -> str:
        """Extract readable text content from HTML using BeautifulSoup."""
        if not BeautifulSoup:
             logger.warning("BeautifulSoup not found, using basic regex for text extraction.")
             # Basic Regex Fallback (less accurate)
             html = re.sub(r"<script.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
             html = re.sub(r"<style.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
             html = re.sub(r"<[^>]+>", " ", html) # Replace tags with space
             text = re.sub(r"\s+", " ", html).strip()
             return self._decode_html_entities(text) # Still decode entities

        try:
            soup = BeautifulSoup(html, 'lxml') # Use lxml parser for speed

            # Remove script, style, head, footer, nav elements
            for element in soup(["script", "style", "head", "footer", "nav", "aside", "form", "button", "input", "textarea", "select"]):
                element.decompose()

            # Get text, joining paragraphs and handling whitespace
            # text = soup.get_text(separator='\n', strip=True)

            # Alternative: Iterate through visible elements for potentially better structure
            body = soup.find('body')
            if not body:
                return soup.get_text(separator='\n', strip=True) # Fallback if no body

            texts = []
            for element in body.find_all(string=True):
                 # Skip text within unwanted tags that might remain
                 if element.parent.name in ["script", "style", "head", "footer", "nav", "aside", "form", "button", "input", "textarea", "select", '[document]']:
                     continue
                 text = element.strip()
                 if text:
                     # Add newline before block elements for better readability
                     if element.parent.name in ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'div', 'li', 'tr', 'th', 'td']:
                          if texts and not texts[-1].endswith('\n'):
                              texts.append('\n')
                     texts.append(text)

            text = ' '.join(texts)
            # Clean up excessive whitespace and newlines
            text = re.sub(r'[ \t]+', ' ', text)
            text = re.sub(r'\n\s*\n', '\n\n', text) # Consolidate multiple newlines

            return self._decode_html_entities(text.strip())

        except Exception as e:
            logger.error(f"BeautifulSoup text extraction failed: {e}")
            return "[Error extracting text]"


    def _decode_html_entities(self, text: str) -> str:
        """Decode HTML entities using the standard html library."""
        try:
            return html.unescape(text)
        except Exception as e:
            logger.warning(f"HTML unescape failed: {e}. Returning original text.")
            return text # Return original text if unescaping fails


class PuppeteerLocalProvider(CapabilityProvider):
    """Local Puppeteer provider for web browsing when Browserless is not available."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize local Puppeteer provider."""
        super().__init__("puppeteer_local", config)
        self.chrome_path = self.config.get("chrome_path", os.environ.get("CHROME_PATH")) # Allow env var override
        self.timeout = self.config.get("timeout", 60) * 1000 # Pyppeteer uses ms
        self.pyppeteer = None # Store imported module

    async def initialize(self) -> None:
        """Initialize the provider."""
        try:
            import importlib.util
            pyppeteer_spec = importlib.util.find_spec("pyppeteer")
            if pyppeteer_spec is None:
                logger.warning("Pyppeteer not installed, local browsing provider will be disabled")
                self.enabled = False
                return

            # Import pyppeteer here
            self.pyppeteer = importlib.import_module("pyppeteer")

            # Check if Chrome executable exists if specified
            if self.chrome_path and not os.path.exists(self.chrome_path):
                 logger.warning(f"Specified Chrome path '{self.chrome_path}' not found. Pyppeteer might download Chromium.")
                 # Don't disable, let Pyppeteer try to handle it

            self.register_capability(CapabilityType.WEB_BROWSING, self.browse_url)
            logger.info("Local Puppeteer provider initialized")
            self.enabled = True
        except Exception as e:
            logger.error(f"Error initializing local Puppeteer provider: {str(e)}")
            self.enabled = False

    async def browse_url(self,
                      url: str,
                      extract_text: bool = True,
                      take_screenshot: bool = False,
                      evaluate_script: Optional[str] = None,
                      wait_for_selector: Optional[str] = None,
                      wait_for_time: Optional[int] = None, # ms
                      **kwargs) -> Dict[str, Any]:
        """Browse a URL using local Puppeteer."""
        if not self.enabled or not self.pyppeteer:
            raise RuntimeError("Local Puppeteer provider is not enabled or failed initialization.")

        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise ValueError(f"Invalid URL: {url}")

        result = {
            "url": url, "title": "", "content": "", "screenshot": None,
            "script_result": None, "status": "error", "error": None
        }
        browser = None
        try:
            launch_options = {
                "headless": True,
                "args": ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"] # Added common args
            }
            if self.chrome_path:
                launch_options["executablePath"] = self.chrome_path

            browser = await self.pyppeteer.launch(**launch_options)
            page = await browser.newPage()
            await page.setViewport({'width': 1280, 'height': 800}) # Set a default viewport

            # Navigate
            await page.goto(url, {"timeout": self.timeout, "waitUntil": "networkidle0"})

            # Waits
            if wait_for_selector:
                await page.waitForSelector(wait_for_selector, {"timeout": self.timeout})
            if wait_for_time:
                await asyncio.sleep(wait_for_time / 1000)

            # Actions (run concurrently if possible, though less critical locally)
            tasks = {}
            if extract_text:
                 tasks['content'] = page.content()
                 tasks['title'] = page.title()
            if take_screenshot:
                 tasks['screenshot'] = page.screenshot({"type": "jpeg", "quality": 80, "fullPage": True})
            if evaluate_script:
                 tasks['script'] = page.evaluate(evaluate_script)

            results_gathered = await asyncio.gather(*tasks.values(), return_exceptions=True)
            # Map results back to tasks for easier processing
            res_map = dict(zip(tasks.keys(), results_gathered))


            # Process results
            if 'title' in res_map:
                 title_res = res_map['title']
                 if isinstance(title_res, Exception):
                      logger.warning(f"Error getting title for {url}: {title_res}")
                 else:
                      result['title'] = title_res

            if 'content' in res_map:
                 content_res = res_map['content']
                 if isinstance(content_res, Exception):
                      logger.error(f"Error getting content for {url}: {content_res}")
                      result['error'] = f"Error getting page content: {content_res}"
                 else:
                      result['content'] = self._extract_text_from_html(content_res)

            if 'screenshot' in res_map:
                 screenshot_res = res_map['screenshot']
                 if isinstance(screenshot_res, Exception):
                      logger.error(f"Error getting screenshot for {url}: {screenshot_res}")
                      if not result["error"]: result["error"] = f"Error taking screenshot: {screenshot_res}"
                 else:
                      result['screenshot'] = screenshot_res

            if 'script' in res_map:
                 script_res = res_map['script']
                 if isinstance(script_res, Exception):
                      logger.error(f"Error evaluating script for {url}: {script_res}")
                      if not result["error"]: result["error"] = f"Error evaluating script: {script_res}"
                 else:
                      result['script_result'] = script_res


            # Determine overall status
            if not result['error']:
                 result['status'] = "success"

        except Exception as e:
            logger.error(f"Error browsing {url} with local Puppeteer: {str(e)}")
            result["error"] = f"Error browsing URL: {str(e)}"
        finally:
            if browser:
                await browser.close()

        return result

    # --- Use the same improved text extraction methods ---
    def _extract_text_from_html(self, html: str) -> str:
        """Extract readable text content from HTML using BeautifulSoup."""
        if not BeautifulSoup:
             logger.warning("BeautifulSoup not found, using basic regex for text extraction.")
             # Basic Regex Fallback (less accurate)
             html = re.sub(r"<script.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
             html = re.sub(r"<style.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
             html = re.sub(r"<[^>]+>", " ", html) # Replace tags with space
             text = re.sub(r"\s+", " ", html).strip()
             return self._decode_html_entities(text) # Still decode entities

        try:
            soup = BeautifulSoup(html, 'lxml') # Use lxml parser for speed

            # Remove script, style, head, footer, nav elements
            for element in soup(["script", "style", "head", "footer", "nav", "aside", "form", "button", "input", "textarea", "select"]):
                element.decompose()

            # Get text, joining paragraphs and handling whitespace
            # text = soup.get_text(separator='\n', strip=True)

            # Alternative: Iterate through visible elements for potentially better structure
            body = soup.find('body')
            if not body:
                return soup.get_text(separator='\n', strip=True) # Fallback if no body

            texts = []
            for element in body.find_all(string=True):
                 # Skip text within unwanted tags that might remain
                 if element.parent.name in ["script", "style", "head", "footer", "nav", "aside", "form", "button", "input", "textarea", "select", '[document]']:
                     continue
                 text = element.strip()
                 if text:
                     # Add newline before block elements for better readability
                     if element.parent.name in ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'div', 'li', 'tr', 'th', 'td']:
                          if texts and not texts[-1].endswith('\n'):
                              texts.append('\n')
                     texts.append(text)

            text = ' '.join(texts)
            # Clean up excessive whitespace and newlines
            text = re.sub(r'[ \t]+', ' ', text)
            text = re.sub(r'\n\s*\n', '\n\n', text) # Consolidate multiple newlines

            return self._decode_html_entities(text.strip())

        except Exception as e:
            logger.error(f"BeautifulSoup text extraction failed: {e}")
            return "[Error extracting text]"


    def _decode_html_entities(self, text: str) -> str:
        """Decode HTML entities using the standard html library."""
        try:
            return html.unescape(text)
        except Exception as e:
            logger.warning(f"HTML unescape failed: {e}. Returning original text.")
            return text # Return original text if unescaping fails
