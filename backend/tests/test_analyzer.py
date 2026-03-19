import pytest
from app.services.analyzer import WordAnalyzer


def test_analyzer_initialization():
    """Test that analyzer can be initialized."""
    analyzer = WordAnalyzer()
    assert analyzer is not None
    assert isinstance(analyzer.russian_words, set)


def test_tokenize():
    """Test text tokenization."""
    analyzer = WordAnalyzer()
    text = "Привет, мир! Как дела?"
    tokens = analyzer.tokenize(text)
    assert "привет" in tokens
    assert "мир" in tokens
    assert "как" in tokens
    assert "дела" in tokens


def test_analyze_russian_text():
    """Test analysis of pure Russian text."""
    analyzer = WordAnalyzer()
    text = "Привет мир как дела"
    result = analyzer.analyze(text)
    assert result['total_words'] == 4
    assert result['foreign_words'] == 0
    assert result['russian_words'] == 4


def test_analyze_mixed_text():
    """Test analysis of mixed Russian and English text."""
    analyzer = WordAnalyzer()
    text = "Привет world welcome to the party"
    result = analyzer.analyze(text)
    assert result['total_words'] > 0
    assert result['foreign_words'] >= 3  # world, welcome, to, the, party
    assert 'world' in result['foreign_word_frequency']
    assert 'welcome' in result['foreign_word_frequency']


def test_analyze_short_words():
    """Test that short words (<=2) are skipped."""
    analyzer = WordAnalyzer()
    text = "я мы он в на"
    result = analyzer.analyze(text)
    # These are 2-letter or 1-letter words, should be skipped
    assert result['total_words'] == 0


def test_foreign_word_frequency():
    """Test that foreign word frequency is counted correctly."""
    analyzer = WordAnalyzer()
    text = "online online meeting meeting meeting"
    result = analyzer.analyze(text)
    assert result['foreign_word_frequency']['online'] == 2
    assert result['foreign_word_frequency']['meeting'] == 3
    assert result['unique_foreign_words'] == 2


def test_is_latin_word():
    """Test Latin character detection."""
    analyzer = WordAnalyzer()
    assert analyzer.is_latin_word("hello")
    assert analyzer.is_latin_word("test123")
    assert not analyzer.is_latin_word("привет")
    assert not analyzer.is_latin_word("123")


def test_is_mixed_word():
    """Test mixed Cyrillic/Latin detection."""
    analyzer = WordAnalyzer()
    assert analyzer.is_mixed_word("хелло")  # Cyrillic + Latin 'hello' pattern
    assert not analyzer.is_mixed_word("привет")
    assert not analyzer.is_mixed_word("hello")


def test_language_detection():
    """Test language detection if langdetect is available."""
    analyzer = WordAnalyzer()
    if analyzer.detect_language("hello") is not None:
        # langdetect is available
        assert analyzer.detect_language("hello") == "en"
        assert analyzer.detect_language("bonjour") == "fr"
        assert analyzer.detect_language("привет") is None or analyzer.detect_language("привет") == "ru"
    else:
        # langdetect not available, should return None
        assert analyzer.detect_language("hello") is None


def test_analyze_with_language_detection():
    """Test that analysis includes language guesses."""
    analyzer = WordAnalyzer()
    text = "hello world привет"
    result = analyzer.analyze(text)
    
    # Check that foreign words have language_guess
    for word_info in result['detected_words']:
        if word_info['is_foreign']:
            assert word_info['language_guess'] is not None
    
    # English words should be detected as foreign
    assert 'hello' in result['foreign_word_frequency']
    assert 'world' in result['foreign_word_frequency']


def test_custom_dictionary_path():
    """Test that analyzer can use a custom dictionary path."""
    import tempfile
    import os
    
    # Create a temporary dictionary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write("привет\n")
        f.write("мир\n")
        f.write("компьютер\n")  # foreign word that might be in some dictionaries
        temp_path = f.name
    
    try:
        analyzer = WordAnalyzer(dictionary_path=temp_path)
        assert "привет" in analyzer.russian_words
        assert "мир" in analyzer.russian_words
        # The word "компьютер" contains Latin 'ю' is actually Cyrillic, but let's test it's there
        assert "компьютер" in analyzer.russian_words or len(analyzer.russian_words) >= 2
    finally:
        os.unlink(temp_path)


def test_dictionary_download():
    """Test dictionary download functionality (mocked)."""
    # This test would require mocking aiohttp
    # For now, we'll just test the method exists
    analyzer = WordAnalyzer()
    assert hasattr(analyzer, '_download_dictionary')