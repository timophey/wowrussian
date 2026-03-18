import pytest
from app.services.parser import HTMLParser


def test_extract_text():
    """Test extracting text from HTML."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test Page</title></head>
    <body>
        <h1>Hello World</h1>
        <p>This is a test paragraph.</p>
        <script>console.log('test');</script>
        <style>body { color: red; }</style>
    </body>
    </html>
    """
    parser = HTMLParser()
    text = parser.extract_text(html)
    
    assert "Hello World" in text
    assert "This is a test paragraph" in text
    assert "console.log" not in text
    assert "color: red" not in text


def test_extract_text_removes_extra_spaces():
    """Test that extract_text normalizes whitespace."""
    html = "<p>  Hello    world  </p>"
    parser = HTMLParser()
    text = parser.extract_text(html)
    
    # Should have normalized spaces
    assert "  " not in text
    assert text.strip() == "Hello world"


def test_extract_links():
    """Test extracting links from HTML."""
    html = """
    <a href="/page1">Page 1</a>
    <a href="https://example.com/page2">Page 2</a>
    <a href="page3">Page 3</a>
    """
    parser = HTMLParser()
    links = parser.extract_links(html, "https://example.com")
    
    assert len(links) >= 3
    assert any('/page1' in link for link in links)
    assert any('https://example.com/page2' in link for link in links)