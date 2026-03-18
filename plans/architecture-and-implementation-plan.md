# План архитектуры и реализации приложения "Анализатор сайтов на иностранные слова"

## Технические решения (на основе ответов пользователя)

- **Бэкенд**: Python + FastAPI
- **Асинхронные задачи**: Celery + Redis (очереди) + asyncio
- **WebSocket**: FastAPI WebSocket + Redis Pub/Sub
- **База данных**: SQLite (хранение метаданных: проекты, страницы, пользователи, статистика)
- **Frontend**: React
- **Веб-сервер**: nginx + Gunicorn
- **Контейнеризация**: Docker + docker-compose
- **Хранение страниц**: Файловое хранилище (каждый пользователь имеет свою директорию)
  - HTML: `storage/{user_id}/{project_id}/html/{page_id}.html`
  - Текст: `storage/{user_id}/{project_id}/text/{page_id}.txt`
- **Изоляция**: Каждый пользователь имеет изолированное хранилище файлов и отдельную SQLite БД (или общая БД с tenant_id)

## Архитектура системы

```
┌─────────────────┐
│   Frontend      │ (React)
└────────┬────────┘
         │ HTTP API + WebSocket
┌────────▼────────┐
│   FastAPI       │
│   (main app)    │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼───┐ ┌──▼────┐
│SQLite  │ │Redis  │
│(мета)  │ │(очереди│
│       │ │+pub/sub)│
└────────┘ └───────┘
         │
┌────────▼────────┐
│   Celery        │
│   Workers       │
│   (crawl+parse) │
└─────────────────┘
         │
┌────────▼────────┐
│  File Storage   │
│  (user_id/)     │
│  - html/        │
│  - text/        │
└─────────────────┘
```

## Детальный план реализации

### Этап 1: Настройка проекта и базовой инфраструктуры

1.1 Создать структуру проекта:
- `backend/` - Python FastAPI приложение
  - `app/` - основное приложение
  - `models/` - SQLAlchemy модели
  - `schemas/` - Pydantic схемы
  - `api/` - эндпоинты
  - `services/` - бизнес-логика (crawler, parser, analyzer, storage)
  - `tasks/` - Celery задачи
  - `core/` - конфигурация, безопасность
  - `storage/` - файловое хранилище (в разработке, в production будет volume)
- `frontend/` - React приложение (Create React App или Vite)
  - `public/`
  - `src/`
    - `components/`
    - `pages/`
    - `services/` (API клиент)
    - `hooks/` (WebSocket)
- `docker/` - Dockerfile и конфиги
- `docs/` - документация
- `nginx/` - конфиги nginx
- `docker-compose.yml`
- `.env.example`
- `storage/` - для разработки (в production будет volume)
- `data/` - для SQLite (в production будет volume)

1.2 Настроить backend:
- requirements.txt (fastapi, uvicorn, sqlalchemy, aiosqlite, celery, redis, beautifulsoup4, aiohttp, websockets, python-multipart, python-jose[cryptography], passlib[bcrypt], etc.)
- config.py (настройки из env)
- database.py (подключение к SQLite, ORM модели)
- models.py (SQLAlchemy модели: User, Project, Page, ForeignWord, etc.)

1.3 Создать Docker конфигурацию:
- Dockerfile для backend
- Dockerfile для frontend (React build)
- docker-compose.yml с сервисами: redis, backend, celery-worker, frontend, nginx
- Volume для хранения файлов: `./storage:/app/storage`
- Volume для SQLite: `./data:/app/data` (или использовать volume docker)

### Этап 2: База данных и модели

2.1 Спроектировать схему БД (SQLite):

**Таблицы:**
- `users` (id, email, password_hash, created_at)
- `projects` (id, user_id, domain, base_url, status, created_at)
- `pages` (id, project_id, url, html_file_path, text_file_path, status, words_count, foreign_words_count, created_at, updated_at)
  - `html_file_path`: относительный путь `storage/{user_id}/{project_id}/html/{page_id}.html`
  - `text_file_path`: относительный путь `storage/{user_id}/{project_id}/text/{page_id}.txt`
- `foreign_words` (id, page_id, word, count, language_guess)
- `crawl_queue` (id, project_id, url, status, attempts, last_attempt_at)

2.2 Создать миграции (Alembic)

2.3 Написать CRUD операции для всех моделей

2.4 Реализовать файловое хранилище:
- Сервис `FileStorage` с методами:
  - `save_html(user_id, project_id, page_id, html_content)`
  - `save_text(user_id, project_id, page_id, text_content)`
  - `get_html_path(user_id, project_id, page_id)`
  - `get_text_path(user_id, project_id, page_id)`
  - `delete_project_files(user_id, project_id)`
- Создание директорий при необходимости
- Обработка ошибок (нет места, нет прав)

### Этап 3: Backend API

(Продолжаем с 3.3, так как 2.4 добавлен в Этап 2)

3.1 Аутентификация:
- Регистрация/логин (JWT токены)
- Middleware для проверки токенов

3.2 API эндпоинты:

**Проекты:**
- `POST /api/projects` - создать проект (ввести URL)
- `GET /api/projects` - список проектов пользователя
- `GET /api/projects/{id}` - детали проекта + статистика
- `DELETE /api/projects/{id}` - удалить проект (и файлы)
- `POST /api/projects/{id}/stop` - остановить сканирование

**Страницы:**
- `GET /api/projects/{project_id}/pages` - список страниц (с пагинацией, фильтрами по статусу)
- `GET /api/projects/{project_id}/pages/{page_id}` - детали страницы + найденные слова
- `GET /api/projects/{project_id}/pages/{page_id}/html` - получить HTML (файл)
- `GET /api/projects/{project_id}/pages/{page_id}/text` - получить текст (файл)

**Статистика:**
- `GET /api/projects/{project_id}/stats` - общая статистика по проекту

3.3 WebSocket эндпоинт:
- `WS /ws/projects/{project_id}` - потоковые обновления статусов

### Этап 4: Сервисы (бизнес-логика)

4.1 URL-обработчик:
- Нормализация URL (оставить только домен + scheme)
- Формирование базового URL
- Валидация URL

4.2 Краулер (Crawler):
- Начало с base_url
- Соблюдение robots.txt
- Извлечение всех ссылок со страниц
- Фильтрация внешних ссылок (только внутри домена)
- Очередь URL для обработки (BFS)
- Ограничение: максимальное количество страниц (настраиваемое, по умолчанию 1000)
- Приоритеты: новые URL → очередь Redis

4.3 Парсер страниц:
- Загрузка HTML (aiohttp)
- Извлечение текста (BeautifulSoup, удаление тегов script/style)
- Очистка текста (удаление лишних пробелов, нормализация)
- Сохранение HTML и текста в БД

4.4 Анализатор иностранных слов:
- Словарь русских слов (загрузить из файла, например, от https://github.com/danakt/russian-words)
- Алгоритм:
  - Токенизация текста (разделение на слова)
  - Приведение к нижнему регистру
  - Удаление пунктуации
  - Проверка каждого слова:
    - Если в словаре → русское
    - Если нет → иностранное
    - Дополнительно: проверка на смешанные слова (русские с латинскими символами)
    - Эвристики: слова с латинскими символами → англицизмы
- Сохранение статистики: общее количество слов, уникальные иностранные слова, их частотность
- Сохранение в таблицу foreign_words

4.5 Менеджер задач (Celery):
- Задачи: crawl_page, parse_page, analyze_page
- Приоритеты и ретраи
- Мониторинг состояния (Redis)

### Этап 5: WebSocket и реальное время

5.1 Настроить Redis Pub/Sub:
- Каналы: `project:{project_id}:updates`
- Публикация событий: page_crawled, page_parsed, page_analyzed, project_completed, project_stopped, error

5.2 Backend WebSocket:
- Подключение к каналу Redis
- Пересылка событий клиенту
- Аутентификация по project_id + JWT

5.3 Frontend WebSocket:
- Подключение при открытии карточки проекта
- Обновление UI в реальном времени:
  - Добавление страниц в очередь/завершённые
  - Обновление счётчиков
  - Уведомления об ошибках

### Этап 9: Разработка Frontend React (главная страница, карточка проекта, детали страницы)

6.1 Настройка React проекта:
- Создать через Create React App или Vite
- Установить зависимости: axios, react-router-dom, @mui/material (или другой UI kit)
- Настроить прокси для API (или CORS на бэкенде)

6.2 Главная страница (`/`):
- Компонент `HomePage`
- Форма с полем ввода URL (валидация URL)
- Кнопка "Анализировать"
- При сабмите: POST /api/projects → редирект на `/project/{id}`

6.3 Страница проекта (`/project/{id}`):
- Компонент `ProjectPage`
- Заголовок: домен, статус (в процессе/завершён/остановлен)
- Статистика (карточки):
  - Всего страниц: X (в очереди: Y, обрабатывается: Z, завершено: W)
  - Найдено иностранных слов: N (уникальных: M)
  - Процент иностранных слов: P%
- Кнопки: "Остановить", "Обновить"
- Список страниц (таблица Material-UI):
  - URL, статус, дата, кол-во иностранных слов
  - Клик → `/project/{project_id}/page/{page_id}`
- WebSocket подключение для реальных обновлений

6.4 Страница деталей страницы (`/project/{project_id}/page/{page_id}`):
- Компонент `PageDetailPage`
- URL, статус, дата обработки
- Статистика: всего слов, иностранных слов, процент
- Список найденных иностранных слов (таблица):
  - Сортировка по частоте (по убыванию)
  - Поиск/фильтрация
  - Колонки: слово, количество
- Кнопки: "Просмотр HTML" (модальное окно/вкладка), "Просмотр текста"

6.5 Список всех проектов (`/projects`):
- Компонент `ProjectsListPage`
- Таблица проектов с краткой статистикой
- Быстрый доступ к деталям

6.6 Дизайн:
- Material-UI (или Tailwind CSS)
- Адаптивность
- Индикаторы загрузки (CircularProgress, Skeleton)
- Уведомления (Snackbar/Toast) об ошибках/успехе
- Тёмная/светлая тема (опционально)

6.7 State management:
- React Context или Redux Toolkit для глобального состояния (проекты, пользователь)
- Локальное состояние для компонентов

### Этап 7: Документация

7.1 README.md (в корне):
- Описание проекта
- Быстрый старт (docker-compose up)
- Конфигурация (.env)

7.2 docs/DEPLOYMENT.md:
- Развёртывание на CloudPanel
- Настройка nginx
- Настройка SSL (Let's Encrypt)
- Настройка firewall
- Мониторинг (логи, метрики)

7.3 docs/API.md:
- Полное описание API эндпоинтов
- Примеры запросов/ответов
- WebSocket протокол

7.4 docs/ARCHITECTURE.md:
- Детали архитектуры
- Поток данных
- Схема БД

7.5 docs/DEVELOPMENT.md:
- Настройка dev-окружения
- Запуск в разработке
- Тестирование
- Добавление новых функций

### Этап 8: Тестирование

8.1 Unit-тесты:
- Тесты для URL-нормализации
- Тесты для парсера
- Тесты для анализатора слов
- Тесты для CRUD операций

8.2 Интеграционные тесты:
- API эндпоинты
- Вебсокет

8.3 End-to-end тесты (опционально):
- Полный цикл: создать проект → сканирование → просмотр результатов

### Этап 9: Деплой и финальная настройка

9.1 Настроить docker-compose для production:
- Использовать gunicorn с multiple workers
- Настроить логирование
- Настроить health checks

9.2 Настроить nginx:
- Проксирование API
- Проксирование WebSocket
- Статика для фронтенда
- SSL (если нужно)

9.3 Настроить Celery:
- Autoscale workers (если нужно)
- Мониторинг (flower)

9.4 Настроить бэкапы БД

9.5 Написать финальную инструкцию по развёртыванию на CloudPanel

## Порядок разработки (рекомендуемый)

1. Настройка проекта, Docker, SQLite + файловое хранилище
2. Модели и миграции (SQLAlchemy + Alembic)
3. Базовый API (проекты без сканирования, аутентификация)
4. Краулер (в фоне, без Celery сначала)
5. Парсер и анализатор
6. Интеграция с Celery
7. WebSocket
8. Frontend React (начинать с базовых компонентов)
9. Тестирование
10. Документация
11. Деплой

## Критические моменты

- **robots.txt**: обязательно проверять и соблюдать
- **Rate limiting**: не спамить сайты, задержки между запросами (настройка User-Agent, задержки)
- **Обработка ошибок**: сетевые ошибки, таймауты, битый HTML
- **Масштабируемость**: обработка больших сайтов (тысячи страниц)
- **Безопасность**: валидация URL, защита от SSRF, ограничение размера ответов
- **Файловое хранилище**:
  - Изоляция пользователей (каждый пользователь - своя папка)
  - Очистка при удалении проекта
  - Ротация/очистка старых файлов (опционально)
- **SQLite**:
  - Включение WAL режима для конкурентного доступа
  - Индексы на часто запрашиваемые поля
  - Резервное копирование (если нужно)
- **Остановка задач**: возможность graceful shutdown Celery задач
- **Конфликты файлов**: уникальные имена файлов (UUID или page_id)

## Git workflow

```
main (production-ready)
├── develop (стабильная dev-ветка)
├── feature/xxx (новые фичи)
├── bugfix/xxx (исправления)
└── hotfix/xxx (критические исправления в production)
```

Каждый коммит должен содержать:
- Чёткое сообщение (что сделано)
- Ссылку на задачу (если есть)
- Неbreaking changes

## Мониторинг и логи

- Логи Celery → файл/stdout
- Логи FastAPI → файл/stdout
- Логи nginx → отдельный файл
- Мониторинг очередей Redis (длина очереди)
- Health check эндпоинт
- Мониторинг дискового пространства (файловое хранилище)

## Дальнейшие улучшения (после релиза)

- [ ] Кэширование результатов (если сайт уже сканировался)
- [ ] Экспорт результатов (CSV, JSON)
- [ ] Сравнение версий сайта (дельта)
- [ ] API для внешних сервисов
- [ ] Графики/визуализация статистики
- [ ] Поддержка других языков (не только русский/английский)
- [ ] Настройка словарей под пользователя
- [ ] Интеграция с Gramota.ru или подобными сервисами