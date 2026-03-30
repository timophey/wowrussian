# Интеграция 168fz с WowRussian Analyzer

## Что было сделано

### 1. Новые компоненты

- **`backend/app/services/fz168_client.py`** - Асинхронный HTTP клиент для 168fz API с retry логикой
- **`backend/app/services/word_analyzer_interface.py`** - Абстракция анализатора:
  - `IWordAnalyzer` - интерфейс
  - `LocalWordAnalyzer` - адаптер для существующего `WordAnalyzer`
  - `HybridWordAnalyzer` - гибридный анализатор с приоритетом 168fz и fallback

### 2. Изменения в моделях

- **`backend/app/models/foreign_word.py`** - добавлено поле `source` для отслеживания источника слова
- Миграция **`backend/alembic/versions/004_add_source_to_foreign_words.py`** - добавляет колонку `source`

### 3. Интеграция в Celery

- **`backend/app/tasks/crawl_tasks.py`**:
  - Заменен `WordAnalyzer` на `HybridWordAnalyzer`
  - Сохранение `source` для `ForeignWord` и `RussianWord`
  - Использование асинхронного вызова `await analyzer.analyze()`

### 4. Конфигурация

- **`backend/app/core/config.py`** - добавлены переменные:
  ```python
  use_fz168: bool = True
  fz168_url: str = "http://localhost:8169"
  fz168_timeout: int = 10
  fz168_retry_attempts: int = 3
  ```

### 5. Docker Compose

- **`docker-compose.yml`** - добавлен опциональный сервис `fz168` (закомментирован)
- Backend и Celery получают переменные окружения для 168fz

### 6. Документация

- **README.md** и **README_RU.md** - добавлены разделы про интеграцию 168fz
- **docs/ARCHITECTURE.md** - обновлена диаграмма и описание компонентов
- **.env.example** - добавлены переменные конфигурации 168fz

### 7. Тесты

- **`backend/tests/test_fz168_client.py`** - тесты клиента (retry, таймауты, ошибки)
- **`backend/tests/test_hybrid_analyzer.py`** - тесты гибридного анализатора и маппинга

## Как протестировать

### 1. Запустить 168fz сервис

**Вариант A (Docker):**
```bash
# Если 168fz уже развернут на production, используйте его URL
# Или запустите локально:
docker run -d -p 8169:8000 timophey/168fz:latest
```

**Вариант B (docker-compose):**
1. Раскомментируйте сервис `fz168` в `docker-compose.yml`
2. Запустите: `docker-compose up -d fz168`

### 2. Настроить WowRussian

В `.env` убедитесь, что указан правильный URL:
```env
USE_FZ168=True
FZ168_URL=http://localhost:8169  # или http://fz168:8000 в docker-compose
```

### 3. Применить миграции

```bash
cd backend
alembic upgrade head
```

Миграция 004 добавит поле `source` в таблицу `foreign_words`.

### 4. Запустить тесты

```bash
cd backend
pytest tests/test_fz168_client.py tests/test_hybrid_analyzer.py -v
```

### 5. Запустить приложение

```bash
# В режиме разработки
cd backend
uvicorn app.main:app --reload

# Или через docker-compose
docker-compose up -d
```

### 6. End-to-End тест

1. Откройте фронтенд: http://localhost:3000
2. Создайте новый проект анализа любого сайта
3. После завершения анализа проверьте базу данных:
   ```sql
   SELECT word, source FROM foreign_words WHERE page_id = <id>;
   ```
   - Если 168fz работал, `source` будет `'fz168'`
   - Если 168fz упал, `source` будет `'dictionary'` или `'fallback'`

4. Проверьте логи Celery:
   ```bash
   docker-compose logs celery-worker
   ```
   Должны быть сообщения:
   - `Successfully used 168fz for analysis` (при успехе)
   - `168fz analysis failed: ..., falling back to local analyzer` (при fallback)

### 7. Тест fallback

1. Остановите 168fz: `docker-compose stop fz168` или остановите контейнер
2. Запустите новый анализ
3. Убедитесь, что анализ завершился успешно
4. В логах Celery должно быть: `Local analyzer used (fallback)`
5. В БД `source` будет `'dictionary'` или `'fallback'`

## Структура изменений

```
wowrussian/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   └── config.py          # +4 поля конфигурации 168fz
│   │   ├── models/
│   │   │   └── foreign_word.py    # + source column
│   │   ├── services/
│   │   │   ├── fz168_client.py    # НОВЫЙ
│   │   │   └── word_analyzer_interface.py  # НОВЫЙ
│   │   └── tasks/
│   │       └── crawl_tasks.py     # замена WordAnalyzer → HybridWordAnalyzer
│   ├── alembic/versions/
│   │   └── 004_add_source_to_foreign_words.py  # НОВЫЙ
│   └── tests/
│       ├── test_fz168_client.py   # НОВЫЙ
│       └── test_hybrid_analyzer.py # НОВЫЙ
├── docker-compose.yml              # + сервис fz168 (закомментирован)
├── .env.example                    # + переменные 168fz
├── README.md                       # + раздел 168fz
├── README_RU.md                    # + раздел 168fz
└── docs/
    ├── ARCHITECTURE.md             # + описание HybridWordAnalyzer
    └── FZ168_INTEGRATION.md        # НОВЫЙ (этот файл)
```

## Откат изменений

Если нужно откатить интеграцию:

1. Отключите 168fz в `.env`:
   ```env
   USE_FZ168=False
   ```

2. В `backend/app/tasks/crawl_tasks.py` верните старый код:
   ```python
   from app.services.analyzer import WordAnalyzer
   # ...
   analyzer = WordAnalyzer()
   analysis = analyzer.analyze(text_content)  # sync call
   ```

3. Удалите поле `source` (осторожно, данные потеряются):
   ```bash
   alembic downgrade -1  # откат миграции 004
   ```

4. Удалите новые файлы:
   ```bash
   rm backend/app/services/fz168_client.py
   rm backend/app/services/word_analyzer_interface.py
   rm backend/tests/test_fz168_client.py
   rm backend/tests/test_hybrid_analyzer.py
   rm backend/alembic/versions/004_add_source_to_foreign_words.py
   ```

## Мониторинг

### Логи

Celery логи содержат информацию об использовании 168fz:
- `Successfully used 168fz for analysis` - анализ через 168fz
- `168fz request timeout` - таймаут
- `168fz analysis failed: ..., falling back` - переход на fallback
- `Local analyzer used (fallback)` - используется локальный анализатор

### Метрики (для будущего)

Можно добавить Prometheus метрики:
- `fz168_requests_total`
- `fz168_success_total`
- `fz168_failure_total`
- `analyzer_fallback_total`

## Известные ограничения

1. **Кеширование**: Нет кеширования запросов к 168fz - каждый анализ отправляется заново
2. **Rate limiting**: Нет лимитации запросов к 168fz (нагружает сервис)
3. **Health check**: Не прерывает текущие задачи при падении 168fz (только новые)
4. **Source tracking**: Для RussianWord source берется из detected_words, но если слово не найдено в detected_words (что маловероятно), source будет NULL

## Будущие улучшения

- [ ] Кеширование результатов 168fz в Redis (по хешу текста)
- [ ] Circuit breaker для быстрого отключения при частых ошибках
- [ ] Метрики в админ-панели
- [ ] Возможность принудительного использования fallback через API
- [ ] Пакетная обработка нескольких страниц одним запросом к 168fz

## Поддержка

При проблемах:
1. Проверьте доступность 168fz: `curl http://localhost:8169/api/v1/health`
2. Проверьте логи: `docker-compose logs backend` и `docker-compose logs celery-worker`
3. Убедитесь, что `USE_FZ168=True` и `FZ168_URL` корректен
4. Проверьте, что миграция 004 применена: `alembic current`
