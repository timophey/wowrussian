import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from aiohttp import ClientConnectorError

from app.services.fz168_client import FZ168Client


def _setup_session_mock(mock_session):
    """Configure a session mock to properly support async with."""
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    return mock_session


def _setup_response_mock(mock_response):
    """Configure a response mock to properly support async with."""
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)
    return mock_response


@pytest.mark.asyncio
class TestFZ168Client:
    """Tests for FZ168Client."""
    
    async def test_check_text_success(self):
        """Test successful text check."""
        client = FZ168Client("http://localhost:8169", timeout=5, retry_attempts=1)
        
        mock_response_data = {
            "all_words": [
                {"word": "привет", "status": "russian"},
                {"word": "hello", "status": "foreign", "language": "en"}
            ],
            "statistics": {}
        }
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = MagicMock()
            _setup_session_mock(mock_session)
            
            mock_response_obj = MagicMock()
            _setup_response_mock(mock_response_obj)
            mock_response_obj.status = 200
            mock_response_obj.json = AsyncMock(return_value=mock_response_data)
            
            mock_session.post.return_value = mock_response_obj
            mock_session_class.return_value = mock_session
            
            result = await client.check_text("привет hello")
            
            assert result == mock_response_data
            mock_session.post.assert_called_once()
    
    async def test_check_text_retry_on_failure(self):
        """Test retry logic on temporary failure."""
        client = FZ168Client("http://localhost:8169", timeout=5, retry_attempts=3)
        
        mock_response_data = {"all_words": [], "statistics": {}}
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = MagicMock()
            _setup_session_mock(mock_session)
            
            mock_response_obj = MagicMock()
            _setup_response_mock(mock_response_obj)
            mock_response_obj.status = 200
            mock_response_obj.json = AsyncMock(return_value=mock_response_data)
            
            call_count = 0
            def mock_post(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count <= 2:
                    raise ClientConnectorError(MagicMock(), OSError("Connection error"))
                return mock_response_obj
            
            mock_session.post.side_effect = mock_post
            mock_session_class.return_value = mock_session
            
            result = await client.check_text("test")
            
            assert result == mock_response_data
            assert call_count == 3
    
    async def test_check_text_timeout(self):
        """Test timeout handling."""
        client = FZ168Client("http://localhost:8169", timeout=1, retry_attempts=2)
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = MagicMock()
            _setup_session_mock(mock_session)
            mock_session.post.side_effect = asyncio.TimeoutError()
            mock_session_class.return_value = mock_session
            
            with pytest.raises(Exception, match="168fz request timeout"):
                await client.check_text("test")
    
    async def test_check_text_http_error(self):
        """Test HTTP error response."""
        client = FZ168Client("http://localhost:8169", timeout=5, retry_attempts=1)
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = MagicMock()
            _setup_session_mock(mock_session)
            
            mock_response_obj = MagicMock()
            _setup_response_mock(mock_response_obj)
            mock_response_obj.status = 500
            mock_response_obj.text = AsyncMock(return_value="Internal Server Error")
            
            mock_session.post.return_value = mock_response_obj
            mock_session_class.return_value = mock_session
            
            with pytest.raises(Exception, match="168fz API error: 500"):
                await client.check_text("test")
    
    async def test_check_text_all_retries_exhausted(self):
        """Test that all retries are exhausted before raising."""
        client = FZ168Client("http://localhost:8169", timeout=5, retry_attempts=2)
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = MagicMock()
            _setup_session_mock(mock_session)
            mock_session.post.side_effect = ClientConnectorError(MagicMock(), OSError("Connection refused"))
            mock_session_class.return_value = mock_session
            
            with pytest.raises(Exception):
                await client.check_text("test")
    
    async def test_health_check_success(self):
        """Test successful health check."""
        client = FZ168Client("http://localhost:8169")
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = MagicMock()
            _setup_session_mock(mock_session)
            
            mock_response = MagicMock()
            _setup_response_mock(mock_response)
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"status": "ok"})
            
            mock_session.get.return_value = mock_response
            mock_session_class.return_value = mock_session
            
            result = await client.health_check()
            
            assert result is True
            mock_session.get.assert_called_once_with("http://localhost:8169/api/v1/health")
    
    async def test_health_check_failure(self):
        """Test health check failure."""
        client = FZ168Client("http://localhost:8169")
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = MagicMock()
            _setup_session_mock(mock_session)
            mock_session.get.side_effect = Exception("Connection error")
            mock_session_class.return_value = mock_session
            
            result = await client.health_check()
            
            assert result is False
