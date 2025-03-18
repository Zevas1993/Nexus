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
from typing import Dict, Any, List, Optional, Union
from urllib.parse import urlparse

from ..abstraction import CapabilityProvider, CapabilityType

logger = logging.getLogger(__name__)

class BrowserlessProvider(CapabilityProvider):
    """Browserless.io provider for web browsing capabilities."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize Browserless provider.
        
        Args:
            config: Provider configuration
        """
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
            
        # Register capabilities
        self.register_capability(CapabilityType.WEB_BROWSING, self.browse_url)
        
        # Test connection
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Cache-Control": "no-cache"}
                params = {"token": self.api_key}
                
                # Simple test request to the content endpoint
                async with session.get(
                    f"{self.api_url}/content",
                    headers=headers,
                    params=params,
                    timeout=10,
                    data=json.dumps({
                        "url": "https://example.com",
                        "waitFor": 1000
                    })
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.warning(f"Browserless API test failed: {error_text}")
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
        """Browse a URL and extract content.
        
        Args:
            url: The URL to browse
            extract_text: Whether to extract text content
            take_screenshot: Whether to take a screenshot
            evaluate_script: JavaScript to execute in the page context
            wait_for_selector: CSS selector to wait for
            wait_for_time: Time to wait in milliseconds
            user_agent: User agent to use
            **kwargs: Additional parameters
            
        Returns:
            Browsing result
        """
        if not self.enabled or not self.api_key:
            raise ValueError("Browserless provider is not enabled")
            
        # Validate URL
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise ValueError(f"Invalid URL: {url}")
            
        # Prepare result
        result = {
            "url": url,
            "title": "",
            "content": "",
            "screenshot": None,
            "script_result": None,
            "status": "error",
            "error": None
        }
        
        # Determine request parameters
        user_agent = user_agent or self.default_user_agent
        wait_for_time = wait_for_time or (self.max_wait if wait_for_selector else 5000)
        
        # For content endpoint (HTML content)
        if extract_text:
            try:
                async with aiohttp.ClientSession() as session:
                    headers = {"Cache-Control": "no-cache"}
                    params = {"token": self.api_key}
                    
                    payload = {
                        "url": url,
                        "waitFor": wait_for_time,
                        "userAgent": user_agent
                    }
                    
                    if wait_for_selector:
                        payload["waitForSelector"] = wait_for_selector
                        
                    async with session.post(
                        f"{self.api_url}/content",
                        headers=headers,
                        params=params,
                        json=payload,
                        timeout=self.timeout
                    ) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            result["error"] = f"Failed to retrieve content: {error_text}"
                        else:
                            html_content = await response.text()
                            
                            # Extract title
                            title_match = re.search(r"<title>(.*?)</title>", html_content, re.IGNORECASE)
                            if title_match:
                                result["title"] = title_match.group(1)
                                
                            # Extract text content from HTML
                            # This is a simple approach - in production would use a more robust HTML parser
                            text_content = self._extract_text_from_html(html_content)
                            result["content"] = text_content
                            result["status"] = "success"
            except Exception as e:
                logger.error(f"Error retrieving content from {url}: {str(e)}")
                result["error"] = f"Error retrieving content: {str(e)}"
                
        # For screenshot endpoint
        if take_screenshot:
            try:
                async with aiohttp.ClientSession() as session:
                    headers = {"Cache-Control": "no-cache"}
                    params = {"token": self.api_key}
                    
                    payload = {
                        "url": url,
                        "waitFor": wait_for_time,
                        "userAgent": user_agent,
                        "options": {
                            "fullPage": True,
                            "type": "jpeg",
                            "quality": 80
                        }
                    }
                    
                    if wait_for_selector:
                        payload["waitForSelector"] = wait_for_selector
                        
                    async with session.post(
                        f"{self.api_url}/screenshot",
                        headers=headers,
                        params=params,
                        json=payload,
                        timeout=self.timeout
                    ) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            logger.error(f"Failed to take screenshot: {error_text}")
                        else:
                            screenshot_data = await response.read()
                            result["screenshot"] = screenshot_data
                            result["status"] = "success"
            except Exception as e:
                logger.error(f"Error taking screenshot of {url}: {str(e)}")
                if not result["error"]:
                    result["error"] = f"Error taking screenshot: {str(e)}"
                    
        # For evaluate endpoint (JavaScript execution)
        if evaluate_script:
            try:
                async with aiohttp.ClientSession() as session:
                    headers = {"Cache-Control": "no-cache"}
                    params = {"token": self.api_key}
                    
                    payload = {
                        "url": url,
                        "waitFor": wait_for_time,
                        "userAgent": user_agent,
                        "code": evaluate_script
                    }
                    
                    if wait_for_selector:
                        payload["waitForSelector"] = wait_for_selector
                        
                    async with session.post(
                        f"{self.api_url}/function",
                        headers=headers,
                        params=params,
                        json=payload,
                        timeout=self.timeout
                    ) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            logger.error(f"Failed to evaluate script: {error_text}")
                        else:
                            script_result = await response.text()
                            result["script_result"] = script_result
                            result["status"] = "success"
            except Exception as e:
                logger.error(f"Error evaluating script on {url}: {str(e)}")
                if not result["error"]:
                    result["error"] = f"Error evaluating script: {str(e)}"
                
        return result
    
    def _extract_text_from_html(self, html: str) -> str:
        """Extract readable text content from HTML.
        
        Args:
            html: HTML content
            
        Returns:
            Extracted text
        """
        # Remove scripts, styles, and other non-content tags
        html = re.sub(r"<script.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<style.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<head.*?</head>", "", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<footer.*?</footer>", "", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<nav.*?</nav>", "", html, flags=re.DOTALL | re.IGNORECASE)
        
        # Replace common block elements with newlines before and after
        html = re.sub(r"<(?:div|p|h[1-6]|section|article|table|ul|ol).*?>", "\n", html, flags=re.IGNORECASE)
        html = re.sub(r"</(?:div|p|h[1-6]|section|article|table|ul|ol)>", "\n", html, flags=re.IGNORECASE)
        
        # Replace list items and table cells with a dash
        html = re.sub(r"<li.*?>", "\n- ", html, flags=re.IGNORECASE)
        html = re.sub(r"<tr.*?>", "\n", html, flags=re.IGNORECASE)
        html = re.sub(r"<td.*?>", " | ", html, flags=re.IGNORECASE)
        
        # Remove all remaining HTML tags
        html = re.sub(r"<[^>]+>", "", html)
        
        # Replace multiple spaces and newlines with a single instance
        text = re.sub(r"\s+", " ", html)
        text = re.sub(r"\n+", "\n", text)
        
        # Decode HTML entities
        text = self._decode_html_entities(text)
        
        return text.strip()
    
    def _decode_html_entities(self, text: str) -> str:
        """Decode HTML entities to their corresponding characters.
        
        Args:
            text: Text with HTML entities
            
        Returns:
            Decoded text
        """
        # Replace common HTML entities
        entities = {
            "&nbsp;": " ",
            "&lt;": "<",
            "&gt;": ">",
            "&amp;": "&",
            "&quot;": "\"",
            "&apos;": "'",
            "&copy;": "©",
            "&reg;": "®"
        }
        
        for entity, char in entities.items():
            text = text.replace(entity, char)
            
        # Replace numeric entities
        text = re.sub(r"&#(\d+);", lambda match: chr(int(match.group(1))), text)
        
        return text


class PuppeteerLocalProvider(CapabilityProvider):
    """Local Puppeteer provider for web browsing when Browserless is not available."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize local Puppeteer provider.
        
        Args:
            config: Provider configuration
        """
        super().__init__("puppeteer_local", config)
        self.chrome_path = self.config.get("chrome_path", "")
        self.timeout = self.config.get("timeout", 60)
        self.puppeteer_enabled = False
        
    async def initialize(self) -> None:
        """Initialize the provider."""
        try:
            # Check if pyppeteer is installed
            import importlib.util
            pyppeteer_spec = importlib.util.find_spec("pyppeteer")
            
            if pyppeteer_spec is None:
                logger.warning("Pyppeteer not installed, local browsing provider will be disabled")
                self.enabled = False
                return
                
            self.puppeteer_enabled = True
            
            # Register capabilities
            self.register_capability(CapabilityType.WEB_BROWSING, self.browse_url)
            
            logger.info("Local Puppeteer provider initialized")
        except Exception as e:
            logger.warning(f"Error initializing local Puppeteer provider: {str(e)}")
            self.enabled = False
            
    async def browse_url(self, 
                      url: str,
                      extract_text: bool = True,
                      take_screenshot: bool = False,
                      evaluate_script: Optional[str] = None,
                      wait_for_selector: Optional[str] = None,
                      wait_for_time: Optional[int] = None,
                      **kwargs) -> Dict[str, Any]:
        """Browse a URL using local Puppeteer.
        
        Args:
            url: The URL to browse
            extract_text: Whether to extract text content
            take_screenshot: Whether to take a screenshot
            evaluate_script: JavaScript to execute in the page context
            wait_for_selector: CSS selector to wait for
            wait_for_time: Time to wait in milliseconds
            **kwargs: Additional parameters
            
        Returns:
            Browsing result
        """
        if not self.enabled or not self.puppeteer_enabled:
            raise ValueError("Local Puppeteer provider is not enabled")
            
        # Validate URL
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise ValueError(f"Invalid URL: {url}")
            
        # Prepare result
        result = {
            "url": url,
            "title": "",
            "content": "",
            "screenshot": None,
            "script_result": None,
            "status": "error",
            "error": None
        }
        
        try:
            from pyppeteer import launch
            
            # Launch browser
            launch_options = {
                "headless": True,
                "args": ["--no-sandbox", "--disable-setuid-sandbox"]
            }
            
            if self.chrome_path:
                launch_options["executablePath"] = self.chrome_path
                
            browser = await launch(**launch_options)
            page = await browser.newPage()
            
            try:
                # Navigate to URL
                response = await page.goto(url, {"timeout": (self.timeout * 1000), "waitUntil": "networkidle0"})
                
                if not response:
                    raise ValueError(f"Failed to navigate to {url}")
                    
                # Wait for selector if specified
                if wait_for_selector:
                    await page.waitForSelector(wait_for_selector, {"timeout": (self.timeout * 1000)})
                    
                # Wait for time if specified
                if wait_for_time:
                    await asyncio.sleep(wait_for_time / 1000)
                    
                # Get page title
                result["title"] = await page.title()
                
                # Extract text content
                if extract_text:
                    content = await page.content()
                    result["content"] = self._extract_text_from_html(content)
                    
                # Take screenshot
                if take_screenshot:
                    screenshot = await page.screenshot({"type": "jpeg", "quality": 80, "fullPage": True})
                    result["screenshot"] = screenshot
                    
                # Evaluate script
                if evaluate_script:
                    script_result = await page.evaluate(evaluate_script)
                    result["script_result"] = script_result
                    
                result["status"] = "success"
            finally:
                await browser.close()
                
        except Exception as e:
            logger.error(f"Error browsing {url} with local Puppeteer: {str(e)}")
            result["error"] = f"Error browsing URL: {str(e)}"
            
        return result
    
    def _extract_text_from_html(self, html: str) -> str:
        """Extract readable text content from HTML.
        
        Args:
            html: HTML content
            
        Returns:
            Extracted text
        """
        # Remove scripts, styles, and other non-content tags
        html = re.sub(r"<script.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<style.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<head.*?</head>", "", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<footer.*?</footer>", "", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<nav.*?</nav>", "", html, flags=re.DOTALL | re.IGNORECASE)
        
        # Replace common block elements with newlines
        html = re.sub(r"<(?:div|p|h[1-6]|section|article|table|ul|ol).*?>", "\n", html, flags=re.IGNORECASE)
        html = re.sub(r"</(?:div|p|h[1-6]|section|article|table|ul|ol)>", "\n", html, flags=re.IGNORECASE)
        
        # Replace list items and table cells with a dash
        html = re.sub(r"<li.*?>", "\n- ", html, flags=re.IGNORECASE)
        html = re.sub(r"<tr.*?>", "\n", html, flags=re.IGNORECASE)
        html = re.sub(r"<td.*?>", " | ", html, flags=re.IGNORECASE)
        
        # Remove all remaining HTML tags
        html = re.sub(r"<[^>]+>", "", html)
        
        # Replace multiple spaces and newlines with a single instance
        text = re.sub(r"\s+", " ", html)
        text = re.sub(r"\n+", "\n", text)
        
        # Decode HTML entities
        text = self._decode_html_entities(text)
        
        return text.strip()
    
    def _decode_html_entities(self, text: str) -> str:
        """Decode HTML entities to their corresponding characters.
        
        Args:
            text: Text with HTML entities
            
        Returns:
            Decoded text
        """
        # Replace common HTML entities
        entities = {
            "&nbsp;": " ",
            "&lt;": "<",
            "&gt;": ">",
            "&amp;": "&",
            "&quot;": "\"",
            "&apos;": "'",
            "&copy;": "©",
            "&reg;": "®"
        }
        
        for entity, char in entities.items():
            text = text.replace(entity, char)
            
        # Replace numeric entities
        text = re.sub(r"&#(\d+);", lambda match: chr(int(match.group(1))), text)
        
        return text
