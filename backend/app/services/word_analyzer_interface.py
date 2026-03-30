from abc import ABC, abstractmethod
from typing import Dict, List, Any
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.core.config import settings
from app.services.analyzer import WordAnalyzer
from app.services.fz168_client import FZ168Client

logger = logging.getLogger(__name__)


class IWordAnalyzer(ABC):
    """Interface for word analysis."""
    
    @abstractmethod
    async def analyze(self, text: str) -> Dict[str, Any]:
        """
        Analyze text and return statistics.
        
        Returns:
            {
                'total_words': int,
                'russian_words': int,
                'foreign_words': int,
                'unique_foreign_words': int,
                'unique_russian_words': int,
                'foreign_word_frequency': {word: count},
                'russian_word_frequency': {word: count},
                'detected_words': list of {word, is_foreign, language_guess, source}
            }
        """
        pass


class LocalWordAnalyzer(IWordAnalyzer):
    """Adapter for the existing synchronous WordAnalyzer to async interface."""
    
    def __init__(self):
        self._analyzer = WordAnalyzer()
    
    async def analyze(self, text: str) -> Dict[str, Any]:
        """Run analysis in thread pool to avoid blocking."""
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as pool:
            result = await loop.run_in_executor(
                pool, 
                lambda: self._analyzer.analyze(text)
            )
        return result


def _map_fz168_response_to_analyzer_format(response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert 168fz API response to WowRussian analyzer format.
    
    168fz response structure:
    {
        "success": true,
        "data": {
            "all_words": [...],
            "statistics": {...},
            "summary": {...},
            "checks": {...},
            "dictionaries_used": [...]
        }
    }
    
    Returns:
        {
            # Standard analyzer fields
            'total_words': int,
            'russian_words': int,
            'foreign_words': int,
            'unique_foreign_words': int,
            'unique_russian_words': int,
            'foreign_word_frequency': {word: count},
            'russian_word_frequency': {word: count},
            'detected_words': [...],
            # 168fz metadata (for storage and display)
            'fz168_metadata': {
                'statistics': {...},      # data.statistics
                'summary': {...},         # data.summary
                'checks': {...},          # data.checks
                'dictionaries': [...]     # data.dictionaries_used
            },
            # Complete raw response from 168fz (for future analysis)
            'fz168_raw_response': {...}
        }
    """
    # Extract all_words from the data field
    data = response.get("data", {})
    all_words = data.get("all_words", [])
    
    total_words = len(all_words)
    russian_count = 0
    foreign_count = 0
    foreign_frequency: Dict[str, int] = {}
    russian_frequency: Dict[str, int] = {}
    detected_words: List[Dict[str, Any]] = []
    
    # Statuses that are considered foreign
    foreign_statuses = {"foreign", "foreign_with_alternative", "prohibited"}
    
    for word_data in all_words:
        word = word_data.get("word", "").lower()
        status = word_data.get("status", "")
        language = word_data.get("language")
        
        is_foreign = status in foreign_statuses
        source = "fz168"
        
        if is_foreign:
            foreign_count += 1
            foreign_frequency[word] = foreign_frequency.get(word, 0) + 1
            language_guess = language if language else "en"
        else:
            russian_count += 1
            russian_frequency[word] = russian_frequency.get(word, 0) + 1
            language_guess = None
        
        detected_words.append({
            "word": word,
            "is_foreign": is_foreign,
            "language_guess": language_guess,
            "source": source
        })
    
    unique_foreign = len(foreign_frequency)
    unique_russian = len(russian_frequency)
    
    # Extract 168fz metadata
    fz168_metadata = {
        'statistics': data.get('statistics', {}),
        'summary': data.get('summary', {}),
        'checks': data.get('checks', {}),
        'dictionaries': data.get('dictionaries_used', [])
    }
    
    return {
        "total_words": total_words,
        "russian_words": russian_count,
        "foreign_words": foreign_count,
        "unique_foreign_words": unique_foreign,
        "unique_russian_words": unique_russian,
        "foreign_word_frequency": foreign_frequency,
        "russian_word_frequency": russian_frequency,
        "detected_words": detected_words,
        "fz168_metadata": fz168_metadata,
        "fz168_raw_response": response
    }


class HybridWordAnalyzer(IWordAnalyzer):
    """
    Hybrid analyzer that uses 168fz service with fallback to local analyzer.
    
    Priority:
    1. Try 168fz if enabled and service is available
    2. Fallback to local WordAnalyzer on any failure
    """
    
    def __init__(self):
        self.use_fz168 = settings.use_fz168
        self.fz168_client = FZ168Client(
            base_url=settings.fz168_url,
            timeout=settings.fz168_timeout,
            retry_attempts=settings.fz168_retry_attempts
        )
        self.local_analyzer = LocalWordAnalyzer()
        self._fz168_available: Optional[bool] = None
    
    async def analyze(self, text: str) -> Dict[str, Any]:
        """
        Analyze text using 168fz with fallback to local analyzer.
        
        Returns:
            Analysis results in WowRussian format
        """
        # If 168fz is disabled, use local immediately
        if not self.use_fz168:
            logger.info("168fz disabled, using local analyzer")
            return await self.local_analyzer.analyze(text)
        
        # Try 168fz
        try:
            logger.debug("Attempting analysis with 168fz")
            response = await self.fz168_client.check_text(text)
            result = _map_fz168_response_to_analyzer_format(response)
            logger.info("Successfully used 168fz for analysis")
            return result
            
        except Exception as e:
            logger.warning(f"168fz analysis failed: {e}, falling back to local analyzer")
            result = await self.local_analyzer.analyze(text)
            logger.info("Local analyzer used (fallback)")
            return result
