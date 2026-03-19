import asyncio
import aiohttp
from urllib.parse import urljoin, urlparse, urldefrag
from typing import Set, List, Optional
import re

from app.core.config import settings


class Crawler:
    """Web crawler service."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.base_domain = urlparse(base_url).netloc
        self.visited_urls: Set[str] = set()
        self.session: Optional[aiohttp.ClientSession] = None
        self.robots_rules: Optional[dict] = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={"User-Agent": settings.crawler_user_agent},
            timeout=aiohttp.ClientTimeout(total=settings.crawler_timeout)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def is_same_domain(self, url: str) -> bool:
        """Check if URL belongs to the same domain."""
        parsed = urlparse(url)
        return parsed.netloc == self.base_domain
    
    def normalize_url(self, url: str) -> str:
        """Normalize URL: remove fragment, ensure scheme."""
        # Remove fragment
        url, _ = urldefrag(url)
        # Ensure it's an absolute URL
        if not url.startswith(('http://', 'https://')):
            url = urljoin(self.base_url, url)
        # Remove trailing slash for consistency
        if url.endswith('/'):
            url = url[:-1]
        return url
    
    async def fetch_robots_txt(self) -> None:
        """Fetch and parse robots.txt."""
        robots_url = f"{self.base_url}/robots.txt"
        try:
            async with self.session.get(robots_url) as response:
                if response.status == 200:
                    content = await response.text()
                    self.robots_rules = self._parse_robots(content)
        except Exception:
            self.robots_rules = None
    
    def _parse_robots(self, content: str) -> dict:
        """Simple robots.txt parser."""
        rules = {"disallow": [], "allow": []}
        current_agent = None
        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                if key == 'user-agent':
                    current_agent = value
                elif key == 'disallow' and current_agent in ('*', settings.crawler_user_agent):
                    rules['disallow'].append(value)
                elif key == 'allow' and current_agent in ('*', settings.crawler_user_agent):
                    rules['allow'].append(value)
        return rules
    
    def is_allowed(self, url: str) -> bool:
        """Check if URL is allowed by robots.txt."""
        if not self.robots_rules:
            return True
        
        parsed = urlparse(url)
        path = parsed.path or '/'
        
        # Check allow rules first (more specific)
        for pattern in self.robots_rules.get('allow', []):
            if self._match_pattern(path, pattern):
                return True
        
        # Check disallow rules
        for pattern in self.robots_rules.get('disallow', []):
            if self._match_pattern(path, pattern):
                return False
        
        return True
    
    def _match_pattern(self, path: str, pattern: str) -> bool:
        """Check if path matches robots.txt pattern."""
        if pattern == '':
            return False
        if pattern.endswith('$'):
            return path == pattern[:-1]
        if pattern.startswith('*'):
            return path.endswith(pattern[1:])
        return path.startswith(pattern)
    
    async def fetch_page(self, url: str) -> Optional[str]:
        """Fetch page content."""
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    content_type = response.headers.get('Content-Type', '')
                    if 'text/html' in content_type:
                        return await response.text()
        except Exception as e:
            print(f"Error fetching {url}: {e}")
        return None
    
    def extract_links(self, html: str, base_url: str) -> List[str]:
        """Extract all links from HTML."""
        links = []
        # Simple regex-based extraction (for now, can use BeautifulSoup)
        href_pattern = re.compile(r'href\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)
        for match in href_pattern.finditer(html):
            href = match.group(1)
            if href.startswith(('http://', 'https://', '/')):
                normalized = self.normalize_url(href)
                if self.is_same_domain(normalized):
                    links.append(normalized)
        return list(set(links))
    
    async def crawl_page(self, url: str, delay: float = settings.crawler_delay) -> Optional[dict]:
        """
        Crawl a single page and return its data with discovered links.
        Returns dict: {url, html, links} or None if failed.
        """
        if url in self.visited_urls:
            return None
        
        if not self.is_allowed(url):
            return None
        
        self.visited_urls.add(url)
        
        html = await self.fetch_page(url)
        if html:
            links = self.extract_links(html, url)
            return {"url": url, "html": html, "links": links}
        
        return None