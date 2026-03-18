import re
from typing import Dict, List, Tuple
from pathlib import Path
import string


class WordAnalyzer:
    """Analyzer for detecting foreign words in Russian text."""
    
    def __init__(self, dictionary_path: str = None):
        self.russian_words: set[str] = set()
        self._load_dictionary(dictionary_path)
    
    def _load_dictionary(self, path: str) -> None:
        """Load Russian words dictionary."""
        if path and Path(path).exists():
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    word = line.strip().lower()
                    if word:
                        self.russian_words.add(word)
        else:
            # Use a minimal built-in dictionary
            # In production, download from https://github.com/danakt/russian-words
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
                # Check for Latin characters
                if self.is_latin_word(word):
                    is_foreign = True
                    language_guess = 'en'  # Assume English for now
                    foreign_count += 1
                    foreign_frequency[word] = foreign_frequency.get(word, 0) + 1
                else:
                    # Word not in dictionary, but no Latin chars
                    # Could be rare Russian word or other Cyrillic-based language
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