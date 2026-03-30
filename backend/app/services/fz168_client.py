import asyncio
import logging
from typing import Dict, Any, Optional
import aiohttp

logger = logging.getLogger(__name__)


class FZ168Client:
    """Async HTTP client for 168fz service."""
    
    def __init__(self, base_url: str, timeout: int = 10, retry_attempts: int = 3):
        """
        Initialize 168fz client.
        
        Args:
            base_url: Base URL of 168fz service (e.g., http://localhost:8169)
            timeout: Request timeout in seconds
            retry_attempts: Number of retry attempts on failure
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.retry_attempts = retry_attempts
    
    async def check_text(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Check text via 168fz API.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with analysis results from 168fz
            
        Raises:
            Exception: If all retry attempts fail
        """
        url = f"{self.base_url}/api/v1/check"
        
        for attempt in range(1, self.retry_attempts + 1):
            try:
                timeout = aiohttp.ClientTimeout(total=self.timeout)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(
                        url,
                        json={"text": text}
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            logger.info(f"168fz request succeeded (attempt {attempt})")
                            return result
                        else:
                            error_text = await response.text()
                            logger.warning(f"168fz returned status {response.status}: {error_text}")
                            if attempt == self.retry_attempts:
                                raise Exception(f"168fz API error: {response.status} - {error_text}")
                            
            except asyncio.TimeoutError:
                logger.warning(f"168fz request timeout (attempt {attempt}/{self.retry_attempts})")
                if attempt == self.retry_attempts:
                    raise Exception("168fz request timeout")
                    
            except Exception as e:
                logger.warning(f"168fz request failed (attempt {attempt}/{self.retry_attempts}): {e}")
                if attempt == self.retry_attempts:
                    raise
        
        # Should not reach here, but just in case
        raise Exception("All retry attempts exhausted")
    
    async def check_url(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Check URL via 168fz API (proxying URL for analysis).
        
        Args:
            url: URL to analyze
            
        Returns:
            Dictionary with analysis results from 168fz
            
        Raises:
            Exception: If all retry attempts fail
        """
        api_url = f"{self.base_url}/api/v1/check"
        
        for attempt in range(1, self.retry_attempts + 1):
            try:
                timeout = aiohttp.ClientTimeout(total=self.timeout)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(
                        api_url,
                        json={"url": url}
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            logger.info(f"168fz URL check succeeded (attempt {attempt})")
                            return result
                        else:
                            error_text = await response.text()
                            logger.warning(f"168fz returned status {response.status}: {error_text}")
                            if attempt == self.retry_attempts:
                                raise Exception(f"168fz API error: {response.status} - {error_text}")
                            
            except asyncio.TimeoutError:
                logger.warning(f"168fz request timeout (attempt {attempt}/{self.retry_attempts})")
                if attempt == self.retry_attempts:
                    raise Exception("168fz request timeout")
                    
            except Exception as e:
                logger.warning(f"168fz request failed (attempt {attempt}/{self.retry_attempts}): {e}")
                if attempt == self.retry_attempts:
                    raise
        
        # Should not reach here, but just in case
        raise Exception("All retry attempts exhausted")
    
    async def health_check(self) -> bool:
        """
        Check if 168fz service is healthy.
        
        Returns:
            True if service is healthy, False otherwise
        """
        try:
            url = f"{self.base_url}/api/v1/health"
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    return response.status == 200
        except Exception as e:
            logger.debug(f"168fz health check failed: {e}")
            return False
