import re
import os
from typing import Dict, List, Optional, Set
from pathlib import Path
import string

try:
    from langdetect import detect, DetectorFactory
    # Set seed for consistent results
    DetectorFactory.seed = 0
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False

from app.core.config import settings


class WordAnalyzer:
    """Analyzer for detecting foreign words in Russian text.
    
    Supports compliance with law №168-FZ by using normative dictionaries.
    """
    
    def __init__(self, dictionary_path: str = None):
        self.russian_words: Set[str] = set()
        self.dictionary_path = dictionary_path or settings.dictionary_path
        self._load_dictionary()
    
    def _download_dictionary(self, url: str, target_path: str) -> bool:
        """Download dictionary from URL."""
        try:
            import aiohttp
            import asyncio
            
            async def fetch():
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            content = await response.text()
                            os.makedirs(os.path.dirname(target_path), exist_ok=True)
                            with open(target_path, 'w', encoding='utf-8') as f:
                                f.write(content)
                            return True
                return False
            
            return asyncio.run(fetch())
        except Exception as e:
            print(f"Failed to download dictionary: {e}")
            return False
    
    def _load_dictionary(self) -> None:
        """Load Russian words dictionary from file or use built-in fallback."""
        path = Path(self.dictionary_path)
        
        # Try to download if auto-download is enabled and file doesn't exist
        if not path.exists() and settings.auto_download_dictionary:
            print(f"Dictionary not found at {path}, attempting to download...")
            success = self._download_dictionary(settings.dictionary_url, str(path))
            if success:
                print(f"Dictionary downloaded to {path}")
        
        # Load dictionary if file exists
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    for line in f:
                        word = line.strip().lower()
                        if word and not word.startswith('#'):
                            # Handle different dictionary formats
                            # Some dictionaries have multiple words per line or definitions
                            # Take only the first word if line contains spaces
                            first_word = word.split()[0] if ' ' in word else word
                            # Remove any non-alphabetic characters
                            first_word = re.sub(r'[^а-яё]', '', first_word)
                            if len(first_word) >= 2:  # Skip very short words
                                self.russian_words.add(first_word)
                print(f"Loaded {len(self.russian_words)} words from dictionary")
            except Exception as e:
                print(f"Error loading dictionary: {e}, using fallback")
                self._load_fallback_dictionary()
        else:
            self._load_fallback_dictionary()
    
    def _load_fallback_dictionary(self) -> None:
        """Load minimal built-in dictionary as fallback."""
        # Common Russian words for basic functionality
        common_words = {
            'и', 'в', 'не', 'что', 'он', 'на', 'я', 'с', 'со', 'как', 'а', 'то', 'все', 'она', 'так',
            'его', 'но', 'да', 'ты', 'к', 'у', 'же', 'вы', 'за', 'бы', 'по', 'только', 'ее', 'мне',
            'было', 'вот', 'от', 'меня', 'еще', 'нет', 'о', 'из', 'ему', 'теперь', 'когда', 'даже',
            'ну', 'вдруг', 'ли', 'если', 'уже', 'или', 'ни', 'быть', 'был', 'него', 'до', 'вас',
            'нибудь', 'опять', 'уж', 'вам', 'ведь', 'там', 'потом', 'себя', 'ничего', 'ей', 'может',
            'они', 'тут', 'где', 'есть', 'надо', 'ней', 'для', 'мы', 'тебя', 'их', 'чем', 'была',
            'сам', 'чтоб', 'без', 'будто', 'чего', 'раз', 'тоже', 'себе', 'под', 'будет', 'ж', 'тогда',
            'кто', 'этот', 'того', 'потому', 'этого', 'какой', 'совсем', 'ним', 'здесь', 'этом',
            'один', 'почти', 'мой', 'тем', 'чтобы', 'нее', 'сейчас', 'были', 'куда', 'зачем', 'всех',
            'никогда', 'можно', 'при', 'наконец', 'два', 'об', 'другой', 'хоть', 'после', 'над',
            'больше', 'тот', 'через', 'эти', 'нас', 'про', 'всего', 'них', 'какая', 'много', 'разве',
            'три', 'эту', 'моя', 'впрочем', 'хорошо', 'свою', 'этой', 'перед', 'иногда', 'лучше',
            'чуть', 'том', 'нельзя', 'такой', 'им', 'более', 'всегда', 'конечно', 'всю', 'между',
            'каждый', 'такие', 'мне', 'тебя', 'меня', 'свои', 'это', 'какие', 'который', 'пока',
            'каждого', 'такая', 'своей', 'своим', 'нашей', 'вашей', 'наших', 'ваших', 'таких',
            'таким', 'такими', 'таком', 'такая', 'такие', 'такого', 'такой', 'такому', 'таком',
            'такое', 'такие', 'таких', 'такими', 'таком', 'такая', 'такое', 'такие'
        }
        self.russian_words = common_words
        print(f"Using fallback dictionary with {len(self.russian_words)} words")
    
    def tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into words.
        Removes punctuation and converts to lowercase.
        """
        # Convert to lowercase
        text = text.lower()
        
        # Replace punctuation with spaces
        for p in string.punctuation:
            text = text.replace(p, ' ')
        
        # Split on whitespace and filter empty tokens
        tokens = [token.strip() for token in text.split() if token.strip()]
        
        return tokens
    
    def is_latin_word(self, word: str) -> bool:
        """Check if word contains Latin characters."""
        return bool(re.search(r'[a-zA-Z]', word))
    
    def is_mixed_word(self, word: str) -> bool:
        """Check if word contains both Cyrillic and Latin characters."""
        has_cyrillic = bool(re.search(r'[а-яА-ЯёЁ]', word))
        has_latin = bool(re.search(r'[a-zA-Z]', word))
        return has_cyrillic and has_latin
    
    def detect_language(self, word: str) -> Optional[str]:
        """Detect language of a word using langdetect."""
        if not LANGDETECT_AVAILABLE:
            return None
        
        try:
            # langdetect works better with longer text
            if len(word) >= 3:
                lang = detect(word)
                return lang
        except Exception:
            return None
        
        return None
    
    def analyze(self, text: str) -> Dict:
        """
        Analyze text and return statistics about foreign words.
        
        Returns:
            {
                'total_words': int,
                'russian_words': int,
                'foreign_words': int,
                'unique_foreign_words': int,
                'foreign_word_frequency': {word: count},
                'detected_words': list of {word, is_foreign, language_guess}
            }
        """
        tokens = self.tokenize(text)
        total_words = len(tokens)
        
        russian_count = 0
        foreign_count = 0
        foreign_frequency: Dict[str, int] = {}
        detected_words: List[Dict] = []
        
        for word in tokens:
            # Skip very short words (1-2 characters)
            if len(word) <= 2:
                continue
            
            is_foreign = False
            language_guess = None
            
            # Check if word is in Russian dictionary
            if word in self.russian_words:
                is_foreign = False
                russian_count += 1
            else:
                # Check for Latin characters - strong indicator of foreign word
                if self.is_latin_word(word):
                    is_foreign = True
                    # Try to detect language
                    language_guess = self.detect_language(word)
                    if not language_guess:
                        language_guess = 'en'  # fallback to English
                    foreign_count += 1
                    foreign_frequency[word] = foreign_frequency.get(word, 0) + 1
                else:
                    # Word not in dictionary, but no Latin chars
                    # Could be rare Russian word, proper noun, or other Cyrillic-based language
                    # For now, treat as Russian (conservative approach)
                    is_foreign = False
                    russian_count += 1
            
            detected_words.append({
                'word': word,
                'is_foreign': is_foreign,
                'language_guess': language_guess
            })
        
        unique_foreign = len(foreign_frequency)
        
        return {
            'total_words': total_words,
            'russian_words': russian_count,
            'foreign_words': foreign_count,
            'unique_foreign_words': unique_foreign,
            'foreign_word_frequency': foreign_frequency,
            'detected_words': detected_words
        }
