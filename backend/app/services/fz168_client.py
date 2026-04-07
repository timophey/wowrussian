import asyncio
import logging
from typing import Dict, Any, Optional, List
import aiohttp

logger = logging.getLogger(__name__)


class FZ168Client:
    """Async HTTP client for 168fz service."""
    
    def __init__(self, base_url: str, timeout: int = 60, retry_attempts: int = 3):
        """
        Initialize 168fz client.
        
        Args:
            base_url: Base URL of 168fz service (e.g., http://localhost:8169)
            timeout: Request timeout in seconds (default: 60)
            retry_attempts: Number of retry attempts on failure
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.retry_attempts = retry_attempts
    
    def _calculate_timeout(self, text: str = None, min_timeout: int = 30) -> int:
        """
        Calculate appropriate timeout based on text length.
        
        Args:
            text: Text to be analyzed (optional)
            min_timeout: Minimum timeout in seconds
            
        Returns:
            Calculated timeout in seconds
        """
        if not text:
            return self.timeout
        
        # Base timeout: 30 seconds minimum
        # Add 1 second per 1000 characters, capped at self.timeout
        char_count = len(text)
        calculated = min_timeout + (char_count // 1000)
        return min(calculated, self.timeout)
    
    async def check_text(self, text: str, allowed_words: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """
        Check text via 168fz API.
        
        Args:
            text: Text to analyze
            allowed_words: Optional list of words to exclude from violations
            
        Returns:
            Dictionary with analysis results from 168fz
            
        Raises:
            Exception: If all retry attempts fail
        """
        url = f"{self.base_url}/api/v1/check"
        
        payload = {"text": text}
        if allowed_words:
            payload["allowed_words"] = allowed_words
        
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Sending to 168fz: text length={len(text)}, allowed_words={allowed_words}")
        
        for attempt in range(1, self.retry_attempts + 1):
            try:
                timeout = aiohttp.ClientTimeout(total=self.timeout)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(
                        url,
                        json=payload
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
    
    async def check_url(self, url: str, allowed_words: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """
        Check URL via 168fz API (proxying URL for analysis).
        
        Args:
            url: URL to analyze
            allowed_words: Optional list of words to exclude from violations
            
        Returns:
            Dictionary with analysis results from 168fz
            
        Raises:
            Exception: If all retry attempts fail
        """
        api_url = f"{self.base_url}/api/v1/check"
        
        payload = {"url": url}
        if allowed_words:
            payload["allowed_words"] = allowed_words
        
        for attempt in range(1, self.retry_attempts + 1):
            try:
                timeout = aiohttp.ClientTimeout(total=self.timeout)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(
                        api_url,
                        json=payload
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
    
    async def check_file(self, file_path: str, filename: str) -> Optional[Dict[str, Any]]:
        """
        Check file via 168fz API.
        
        Args:
            file_path: Path to the file to analyze
            filename: Original filename
            
        Returns:
            Dictionary with analysis results from 168fz
            
        Raises:
            Exception: If all retry attempts fail
        """
        url = f"{self.base_url}/api/v1/check/file"
        
        for attempt in range(1, self.retry_attempts + 1):
            try:
                timeout = aiohttp.ClientTimeout(total=self.timeout)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    with open(file_path, 'rb') as f:
                        form_data = aiohttp.FormData()
                        form_data.add_field('file', f, filename=filename)
                        
                        async with session.post(url, data=form_data) as response:
                            if response.status == 200:
                                result = await response.json()
                                logger.info(f"168fz file check succeeded (attempt {attempt})")
                                return result
                            else:
                                error_text = await response.text()
                                logger.warning(f"168fz returned status {response.status}: {error_text}")
                                if attempt == self.retry_attempts:
                                    raise Exception(f"168fz API error: {response.status} - {error_text}")
                                
            except asyncio.TimeoutError:
                logger.warning(f"168fz file request timeout (attempt {attempt}/{self.retry_attempts})")
                if attempt == self.retry_attempts:
                    raise Exception("168fz file request timeout")
                    
            except Exception as e:
                logger.warning(f"168fz file request failed (attempt {attempt}/{self.retry_attempts}): {e}")
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
