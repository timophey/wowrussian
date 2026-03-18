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