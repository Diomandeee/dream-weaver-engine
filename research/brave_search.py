"""
Brave Search API client for dream research.

Handles multi-query search, rate limiting, and content extraction.
"""

import os
import time
import requests
from typing import Optional


class BraveSearchClient:
    """Search the web via Brave Search API."""
    
    BASE_URL = "https://api.search.brave.com/res/v1/web/search"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("BRAVE_API_KEY")
        if not self.api_key:
            raise ValueError("BRAVE_API_KEY not set")
        self.session = requests.Session()
        self.session.headers.update({
            "X-Subscription-Token": self.api_key,
            "Accept": "application/json",
        })
        self._last_request = 0
        self._min_interval = 1.0  # 1 second between requests (rate limit safety)
    
    def _rate_limit(self):
        """Ensure we don't exceed rate limits."""
        elapsed = time.time() - self._last_request
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request = time.time()
    
    def search(
        self,
        query: str,
        count: int = 10,
        country: str = "US",
        freshness: Optional[str] = None,
        search_lang: str = "en",
    ) -> list[dict]:
        """
        Search Brave and return structured results.
        
        Args:
            query: Search query string
            count: Number of results (1-20)
            country: 2-letter country code
            freshness: 'pd' (24h), 'pw' (week), 'pm' (month), 'py' (year), or date range
            search_lang: Language code
        
        Returns:
            List of {title, url, snippet, age, extra_snippets}
        """
        self._rate_limit()
        
        params = {
            "q": query,
            "count": min(count, 20),
            "country": country,
            "search_lang": search_lang,
            "text_decorations": False,
        }
        if freshness:
            params["freshness"] = freshness
        
        try:
            response = self.session.get(self.BASE_URL, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            print(f"    [Brave] Search failed for '{query[:50]}': {e}")
            return []
        
        results = []
        for item in data.get("web", {}).get("results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("description", ""),
                "age": item.get("age", ""),
                "extra_snippets": item.get("extra_snippets", []),
                "language": item.get("language", "en"),
                "family_friendly": item.get("family_friendly", True),
            })
        
        # Also grab news results if available
        for item in data.get("news", {}).get("results", [])[:3]:
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("description", ""),
                "age": item.get("age", ""),
                "extra_snippets": [],
                "source": "news",
            })
        
        return results
    
    def fetch_page_content(self, url: str, max_chars: int = 8000) -> Optional[str]:
        """
        Fetch and extract readable content from a URL.
        
        Uses a simple text extraction approach — enough for research context.
        """
        self._rate_limit()
        
        try:
            response = requests.get(
                url,
                timeout=10,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; DreamResearchBot/1.0)",
                    "Accept": "text/html,application/xhtml+xml,text/plain",
                },
                allow_redirects=True,
            )
            response.raise_for_status()
            
            content_type = response.headers.get("Content-Type", "")
            if "text/html" in content_type:
                return self._extract_text_from_html(response.text, max_chars)
            elif "text/plain" in content_type:
                return response.text[:max_chars]
            else:
                return None
                
        except Exception as e:
            print(f"    [Fetch] Failed for {url[:60]}: {e}")
            return None
    
    def _extract_text_from_html(self, html: str, max_chars: int) -> str:
        """Simple HTML to text extraction without heavy dependencies."""
        import re
        
        # Remove script and style blocks
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<nav[^>]*>.*?</nav>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<footer[^>]*>.*?</footer>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<header[^>]*>.*?</header>', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Convert block elements to newlines
        text = re.sub(r'<(?:p|div|br|h[1-6]|li|tr)[^>]*>', '\n', text, flags=re.IGNORECASE)
        
        # Remove all remaining tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Decode entities
        text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        text = text.replace('&nbsp;', ' ').replace('&quot;', '"').replace('&#39;', "'")
        
        # Clean whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        text = text.strip()
        
        return text[:max_chars]
