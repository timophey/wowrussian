import re
from typing import Tuple
from bs4 import BeautifulSoup


class HTMLParser:
    """HTML parser service for extracting text."""
    
    @staticmethod
    def extract_text(html: str) -> str:
        """
        Extract clean text from HTML.
        Removes scripts, styles, and normalizes whitespace.
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove script and style elements
        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            element.decompose()
        
        # Get text
        text = soup.get_text()
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text
    
    @staticmethod
    def extract_links(html: str, base_url: str) -> list[str]:
        """Extract all links from HTML."""
        soup = BeautifulSoup(html, 'html.parser')
        links = []
        
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            if href.startswith(('http://', 'https://', '/')):
                links.append(href)
        
        return links