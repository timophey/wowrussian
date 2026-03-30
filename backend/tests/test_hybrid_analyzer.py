import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from aiohttp import ClientResponseError, ClientConnectorError

from app.services.word_analyzer_interface import (
    HybridWordAnalyzer,
    LocalWordAnalyzer,
    _map_fz168_response_to_analyzer_format
)
from app.services.analyzer import WordAnalyzer


class TestLocalWordAnalyzer:
    """Tests for LocalWordAnalyzer."""
    
    @pytest.mark.asyncio
    async def test_analyze(self):
        """Test that LocalWordAnalyzer wraps WordAnalyzer correctly."""
        analyzer = LocalWordAnalyzer()
        
        # Mock the underlying WordAnalyzer
        with patch.object(WordAnalyzer, 'analyze') as mock_analyze:
            mock_analyze.return_value = {
                'total_words': 3,
                'russian_words': 2,
                'foreign_words': 1,
                'unique_foreign_words': 1,
                'unique_russian_words': 2,
                'foreign_word_frequency': {'hello': 1},
                'russian_word_frequency': {'привет': 1, 'мир': 1},
                'detected_words': [
                    {'word': 'привет', 'is_foreign': False, 'language_guess': None, 'source': 'dictionary'},
                    {'word': 'hello', 'is_foreign': True, 'language_guess': 'en', 'source': 'dictionary'},
                    {'word': 'мир', 'is_foreign': False, 'language_guess': None, 'source': 'dictionary'}
                ]
            }
            
            result = await analyzer.analyze("привет hello мир")
            
            assert result['total_words'] == 3
            assert result['foreign_words'] == 1
            assert result['russian_words'] == 2
            mock_analyze.assert_called_once_with("привет hello мир")


class TestMapFZ168Response:
    """Tests for _map_fz168_response_to_analyzer_format function."""
    
    def test_map_all_statuses(self):
        """Test mapping all possible statuses from 168fz."""
        response = {
            "success": True,
            "data": {
                "all_words": [
                    {"word": "привет", "status": "russian"},
                    {"word": "компьютер", "status": "foreign", "language": "en"},
                    {"word": "менеджер", "status": "foreign_with_alternative", "language": "en"},
                    {"word": "бред", "status": "prohibited", "language": "ru"},
                    {"word": "тест", "status": "allowed", "language": "en"}
                ]
            }
        }
        
        result = _map_fz168_response_to_analyzer_format(response)
        
        assert result['total_words'] == 5
        assert result['foreign_words'] == 3  # foreign, foreign_with_alternative, prohibited
        assert result['russian_words'] == 2  # russian, allowed
        assert result['unique_foreign_words'] == 3
        assert result['unique_russian_words'] == 2
        
        # Check foreign word frequency
        assert result['foreign_word_frequency']['компьютер'] == 1
        assert result['foreign_word_frequency']['менеджер'] == 1
        assert result['foreign_word_frequency']['бред'] == 1
        
        # Check russian word frequency
        assert result['russian_word_frequency']['привет'] == 1
        assert result['russian_word_frequency']['тест'] == 1
        
        # Check detected_words sources are all 'fz168'
        for word_data in result['detected_words']:
            assert word_data['source'] == 'fz168'
            if word_data['is_foreign']:
                assert word_data['language_guess'] is not None
    
    def test_map_empty_response(self):
        """Test mapping empty response."""
        response = {"success": True, "data": {"all_words": []}}
        result = _map_fz168_response_to_analyzer_format(response)
        
        assert result['total_words'] == 0
        assert result['foreign_words'] == 0
        assert result['russian_words'] == 0
        assert result['foreign_word_frequency'] == {}
        assert result['russian_word_frequency'] == {}
        assert result['detected_words'] == []
    
    def test_map_duplicate_words(self):
        """Test that duplicate words are counted correctly."""
        response = {
            "success": True,
            "data": {
                "all_words": [
                    {"word": "hello", "status": "foreign", "language": "en"},
                    {"word": "hello", "status": "foreign", "language": "en"},
                    {"word": "мир", "status": "russian"}
                ]
            }
        }
        
        result = _map_fz168_response_to_analyzer_format(response)
        
        assert result['total_words'] == 3
        assert result['foreign_words'] == 2
        assert result['unique_foreign_words'] == 1
        assert result['foreign_word_frequency']['hello'] == 2
        assert result['russian_word_frequency']['мир'] == 1
    
    def test_map_missing_status(self):
        """Test handling of words with missing status (treated as russian)."""
        response = {
            "success": True,
            "data": {
                "all_words": [
                    {"word": "test"}  # No status field
                ]
            }
        }
        
        result = _map_fz168_response_to_analyzer_format(response)
        
        assert result['total_words'] == 1
        assert result['russian_words'] == 1
        assert result['foreign_words'] == 0
    
    def test_map_includes_raw_response(self):
        """Test that raw 168fz response is included in the result."""
        response = {
            "success": True,
            "data": {
                "all_words": [
                    {"word": "test", "status": "russian"}
                ],
                "statistics": {"total": 1},
                "summary": {"has_foreign": False},
                "checks": {"valid": True},
                "dictionaries_used": ["dict1"]
            }
        }
        
        result = _map_fz168_response_to_analyzer_format(response)
        
        # Verify raw response is included and equals the original response
        assert 'fz168_raw_response' in result
        assert result['fz168_raw_response'] == response
        # Also verify metadata is extracted correctly
        assert result['fz168_metadata']['statistics'] == {"total": 1}
        assert result['fz168_metadata']['summary'] == {"has_foreign": False}
        assert result['fz168_metadata']['checks'] == {"valid": True}
        assert result['fz168_metadata']['dictionaries'] == ["dict1"]


class TestHybridWordAnalyzer:
    """Tests for HybridWordAnalyzer."""
    
    @pytest.mark.asyncio
    async def test_analyze_uses_fz168_when_enabled_and_available(self):
        """Test that 168fz is used when enabled and available."""
        with patch('app.services.word_analyzer_interface.settings') as mock_settings:
            mock_settings.use_fz168 = True
            mock_settings.fz168_url = "http://test:8000"
            mock_settings.fz168_timeout = 5
            mock_settings.fz168_retry_attempts = 1
            
            analyzer = HybridWordAnalyzer()
            
            # Mock the FZ168 client
            mock_fz168_response = {
                "success": True,
                "data": {
                    "all_words": [
                        {"word": "test", "status": "russian"}
                    ]
                }
            }
            with patch.object(analyzer.fz168_client, 'check_text', new_callable=AsyncMock) as mock_check:
                mock_check.return_value = mock_fz168_response
                
                result = await analyzer.analyze("test")
                
                assert result['total_words'] == 1
                assert result['russian_words'] == 1
                mock_check.assert_called_once_with("test")
    
    @pytest.mark.asyncio
    async def test_analyze_fallback_when_fz168_fails(self):
        """Test fallback to local analyzer when 168fz fails."""
        with patch('app.services.word_analyzer_interface.settings') as mock_settings:
            mock_settings.use_fz168 = True
            mock_settings.fz168_url = "http://test:8000"
            mock_settings.fz168_timeout = 5
            mock_settings.fz168_retry_attempts = 1
            
            analyzer = HybridWordAnalyzer()
            
            # Mock FZ168 to fail
            with patch.object(analyzer.fz168_client, 'check_text', new_callable=AsyncMock) as mock_check:
                mock_check.side_effect = Exception("Service unavailable")
                
                # Mock local analyzer
                local_result = {
                    'total_words': 2,
                    'russian_words': 2,
                    'foreign_words': 0,
                    'unique_foreign_words': 0,
                    'unique_russian_words': 2,
                    'foreign_word_frequency': {},
                    'russian_word_frequency': {'привет': 1, 'мир': 1},
                    'detected_words': [
                        {'word': 'привет', 'is_foreign': False, 'language_guess': None, 'source': 'dictionary'},
                        {'word': 'мир', 'is_foreign': False, 'language_guess': None, 'source': 'dictionary'}
                    ]
                }
                with patch.object(analyzer.local_analyzer, 'analyze', new_callable=AsyncMock) as mock_local:
                    mock_local.return_value = local_result
                    
                    result = await analyzer.analyze("привет мир")
                    
                    assert result == local_result
                    mock_check.assert_called_once()
                    mock_local.assert_called_once_with("привет мир")
    
    @pytest.mark.asyncio
    async def test_analyze_uses_local_when_disabled(self):
        """Test that local analyzer is used when 168fz is disabled."""
        with patch('app.services.word_analyzer_interface.settings') as mock_settings:
            mock_settings.use_fz168 = False
            
            analyzer = HybridWordAnalyzer()
            
            # Mock local analyzer
            local_result = {
                'total_words': 1,
                'russian_words': 1,
                'foreign_words': 0,
                'unique_foreign_words': 0,
                'unique_russian_words': 1,
                'foreign_word_frequency': {},
                'russian_word_frequency': {'тест': 1},
                'detected_words': [
                    {'word': 'тест', 'is_foreign': False, 'language_guess': None, 'source': 'dictionary'}
                ]
            }
            with patch.object(analyzer.local_analyzer, 'analyze', new_callable=AsyncMock) as mock_local, \
                 patch.object(analyzer.fz168_client, 'check_text', new_callable=AsyncMock) as mock_check:
                mock_local.return_value = local_result
                
                result = await analyzer.analyze("тест")
                
                assert result == local_result
                # FZ168 client should not be called
                mock_check.assert_not_called()
                mock_local.assert_called_once_with("тест")
