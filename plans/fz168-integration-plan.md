# План интеграции микросервиса 168fz в WowRussian Analyzer

## Цель
Интегрировать микросервис 168fz для расширенной проверки соответствия закону №168-ФЗ с graceful degradation на текущую локальную реализацию.

## Конфигурация

### Переменные окружения (backend/.env)
```env
USE_FZ168=True
FZ168_URL=http://localhost:8169
FZ168_TIMEOUT=10
FZ168_RETRY_ATTEMPTS=3
```

### Конфигурация в коде
Добавить в `backend/app/core/config.py`:
```python
use_fz168: bool = Field(default=True, env="USE_FZ168")
fz168_url: str = Field(default="http://localhost:8169", env="FZ168_URL")
fz168_timeout: int = Field(default=10, env="FZ168_TIMEOUT")
fz168_retry_attempts: int = Field(default=3, env="FZ168_RETRY_ATTEMPTS")
```

## Архитектурные изменения

### 1. Создание абстракции анализатора

**Файл: `backend/app/services/word_analyzer_interface.py`**

```python
from abc import ABC, abstractmethod
from typing import Dict, List

class IWordAnalyzer(ABC):
    """Interface for word analysis."""
    
    @abstractmethod
    async def analyze(self, text: str) -> Dict:
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
```

**Класс `LocalWordAnalyzer`** - обертка вокруг существующего `WordAnalyzer` (синхронный → асинхронный адаптер)

**Класс `HybridWordAnalyzer`** - основной класс:
- Приоритет: 168fz
- Fallback: LocalWordAnalyzer при ошибках/таймаутах
- Логирование: какой анализатор использовался
- Сохранение источника слова в `detected_words[*]['source']`:
  - `'fz168'` - из 168fz
  - `'dictionary'` - из основного словаря
  - `'fallback'` - из fallback словаря

### 2. Клиент для 168fz API

**Файл: `backend/app/services/fz168_client.py`**

```python
import aiohttp
from typing import Dict, Any
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

class FZ168Client:
    """Async HTTP client for 168fz service."""
    
    def __init__(self, base_url: str, timeout: int = 10, retry_attempts: int = 3):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.retry_attempts = retry_attempts
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def check_text(self, text: str) -> Dict[str, Any]:
        """
        Check text via 168fz API.
        
        Returns raw response from 168fz.
        Raises exception on failure.
        """
        url = f"{self.base_url}/api/v1/check"
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json={"text": text},
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                if response.status != 200:
                    raise Exception(f"168fz returned status {response.status}")
                return await response.json()
```

### 3. Маппинг результатов 168fz → формат WowRussian

**Метод `_map_fz168_response_to_analyzer_format(response: dict) -> dict`**

Маппинг статусов 168fz:
- `russian` → `is_foreign=False`, `source='fz168'`
- `allowed` → `is_foreign=False`, `source='fz168'`
- `foreign` → `is_foreign=True`, `language_guess` из поля `language` или `'en'`
- `foreign_with_alternative` → `is_foreign=True`, `language_guess` из `language`
- `prohibited` → `is_foreign=True`, `language_guess` из `language`

Структура `all_words` в 168fz:
```json
{
  "all_words": [
    {"word": "developer", "status": "foreign", "language": "en", ...},
    {"word": "программист", "status": "russian", ...}
  ]
}
```

Преобразуем в:
```python
{
    'total_words': len(all_words),
    'russian_words': count(russian/status),
    'foreign_words': count(foreign/status),
    'unique_foreign_words': len(unique foreign words),
    'unique_russian_words': len(unique russian words),
    'foreign_word_frequency': {word: count},
    'russian_word_frequency': {word: count},
    'detected_words': [
        {'word': word, 'is_foreign': bool, 'language_guess': lang, 'source': 'fz168'}
    ]
}
```

### 4. Интеграция в Celery задачи

**Файл: `backend/app/tasks/crawl_tasks.py`**

Изменения:
- Импорт `HybridWordAnalyzer`
- Заменить `analyzer = WordAnalyzer()` на `analyzer = HybridWordAnalyzer()`
- В `_analyze_page_in_session` и `_parse_and_analyze_page_async`

### 5. Обновление моделей БД (опционально)

Если нужно хранить источник слова отдельно, можно:
- Добавить поле `source` в модель `RussianWord` (уже есть)
- Добавить поле `source` в модель `ForeignWord` (нужно добавить)

**Миграция Alembic:**
```python
op.add_column('foreign_words', sa.Column('source', sa.String(), nullable=True))
```

### 6. Docker Compose

**Файл: `docker-compose.yml`**

Добавить сервис `fz168` (закомментирован по умолчанию):
```yaml
  # fz168:
  #   image: timophey/168fz:latest
  #   container_name: wowrussian-fz168
  #   ports:
  #     - "8169:8000"
  #   volumes:
  #     - ./dictionaries:/app/dictionaries
  #   environment:
  #     - ADMIN_KEY=${FZ168_ADMIN_KEY:-}
  #     - DEBUG=false
  #   networks:
  #     - wowrussian-network
  #   restart: unless-stopped
```

Или оставить как внешний сервис, настраиваемый через `FZ168_URL`.

### 7. Логирование и мониторинг

Добавить логи:
```python
import logging
logger = logging.getLogger(__name__)

# В HybridWordAnalyzer:
logger.info(f"Using 168fz for analysis (attempt {attempt})")
logger.warning(f"168fz failed: {error}, falling back to local analyzer")
logger.info(f"Local analyzer used (fallback)")
```

Метрики (опционально, через Prometheus или логи):
- `fz168.success`
- `fz168.failure`
- `fz168.timeout`
- `analyzer.fallback.used`

### 8. Тесты

**Файл: `backend/tests/test_hybrid_analyzer.py`**

- Тест успешного вызова 168fz
- Тест fallback при 168fz недоступен
- Тест fallback при таймауте
- Тест fallback при invalid response
- Тест маппинга статусов
- Тест сохранения источника слова

Использовать моки для aiohttp.

### 9. Документация

**README.md / README_RU.md:**
- Добавить секцию "Интеграция с 168fz"
- Описать конфигурационные переменные
- Инструкция по запуску с 168fz

**docs/ARCHITECTURE.md:**
- Обновить диаграмму архитектуры
- Добавить описание `HybridWordAnalyzer`
- Описать flow: 168fz → fallback → результат

**docs/DEVELOPMENT.md:**
- Как запустить с 168fz локально
- Как тестировать fallback

### 10. Развертывание

**Production:**
1. Развернуть 168fz на отдельном сервере/контейнере
2. Установить `USE_FZ168=True` и `FZ168_URL=http://<server>:8169`
3. Настроить сеть/файрволл для доступа
4. Мониторить метрики fallback

**Development:**
1. Раскомментировать сервис `fz168` в docker-compose.yml
2. Или указать `FZ168_URL=http://localhost:8169` если 168fz запущен отдельно

## Порядок реализации

1. ✅ Анализ текущей архитектуры
2. ✅ Проектирование абстракции
3. Добавить конфигурационные переменные в `config.py`
4. Создать `fz168_client.py` с retry логикой
5. Создать `word_analyzer_interface.py` с `LocalWordAnalyzer` и `HybridWordAnalyzer`
6. Обновить модель `ForeignWord` (добавить `source`) → создать миграцию
7. Интегрировать `HybridWordAnalyzer` в `crawl_tasks.py`
8. Добавить логирование
9. Обновить `docker-compose.yml` (добавить опциональный сервис fz168)
10. Написать unit тесты
11. Обновить документацию
12. Протестировать end-to-end

## Обратная совместимость

- При `USE_FZ168=False` используется только локальный анализатор
- При недоступности 168fz автоматически fallback на локальный
- Формат вывода `analyze()` полностью совместим с существующим кодом
- Существующие тесты продолжают работать (если не тестировать новый код)

## Риски и митигация

| Риск | Митигация |
|------|-----------|
| 168fz недоступен → задержка анализа | Таймаут 10 сек, быстрый fallback |
| Изменение API 168fz | Абстракция клиента, легко заменить |
| 168fz возвращает ошибку 500 | Retry + fallback |
| Несовместимость форматов | Тесты маппинга, валидация |
| Нагрузка на 168fz | Кеширование (опционально в будущем) |

## Метрики успеха

- ✅ 95%+ запросов успешно обрабатываются 168fz (не попадают в fallback)
- ✅ Fallback работает корректно при недоступности 168fz
- ✅ Нет регрессии в существующей функциональности
- ✅ Логирование переходов на fallback
- ✅ Все тесты проходят

## Дополнительные улучшения (пост-релиз)

- Кеширование результатов 168fz (Redis) для повторяющихся текстов
- Конфигурация: список "разрешенных иностранных терминов" на уровне WowRussian
- Статистика использования 168fz в админ-панели
- Возможность принудительного использования fallback через API
