# WowRussian Analyzer

**Веб-приложение для анализа сайтов и обнаружения иностранных слов и англицизмов**

---

## 📋 О проекте

**WowRussian Analyzer** — это полнофункциональное веб-приложение, предназначенное для анализа веб-сайтов на наличие иностранных слов и англицизмов в русскоязычном контенте. Приложение автоматически сканирует сайты, извлекает текстовый контент и сравнивает его с нормативными словарями русского языка (в соответствии с требованиями закона №168-ФЗ).

### 🎯 Основные возможности

- **Анализ сайтов** — ввод URL и автоматический обход страниц в пределах домена
- **Извлечение текста** — парсинг HTML и извлечение чистого текстового контента
- **Обнаружение иностранных слов** — использование **168fz микросервиса** или локальных словарей (соответствие закону №168-ФЗ)
- **Статистика в реальном времени** — детальная статистика по найденным словам, частоте использования
- **WebSocket уведомления** — мгновенные обновления о ходе анализа
- **Многопользовательский режим** — изолированное хранение данных для каждого пользователя
- **Асинхронная обработка** — использование Celery для фоновых задач обхода сайтов
- **Graceful degradation** — автоматический переход на локальный анализатор при недоступности 168fz
- **Соответствие 152-ФЗ** — полная реализация требований Федерального закона "О персональных данных" (см. ниже)

---

## 🚀 Быстрый старт

### 📦 Предварительные требования

- **Docker** и **Docker Compose** (рекомендуется)
- **Node.js 18+** (для разработки фронтенда)
- **Git** (для клонирования репозитория)

### 🐳 Запуск через Docker (рекомендуемый способ)

#### 1. Клонируйте репозиторий **с субмодулями**

```bash
git clone --recurse-submodules <repository-url>
cd wowrussian
```

**Если вы уже клонировали без субмодулей**, инициализируйте их:
```bash
git submodule update --init --recursive
```

#### 2. Настройте переменные окружения

```bash
cp .env.example .env
```

Отредактируйте файл `.env`:

```env
# Обязательно измените секретный ключ для production!
SECRET_KEY=ваш-секретный-ключ-здесь

# Выберите базу данных (по умолчанию SQLite):
DATABASE_URL=postgresql+asyncpg://wowrussian:wowrussian_password@postgres:5432/wowrussian

# Для SQLite (разработка):
# DATABASE_URL=sqlite+aiosqlite:///./data/app.db
```

#### 3. Запустите все сервисы

```bash
# С PostgreSQL (production)
docker-compose up -d

# Или с SQLite (разработка, по умолчанию)
# docker-compose up -d
```

#### 4. Откройте приложение

- **Фронтенд:** http://localhost:3000 (настраивается через `FRONTEND_PORT` в `.env`)
- **Бэкенд API:** http://localhost:8000
- **Документация API:** http://localhost:8000/docs
- **WebSocket:** `ws://localhost:8000/ws/projects/{project_id}`

---

### 💻 Разработка

#### Бэкенд

```bash
cd backend

# Создание виртуального окружения
python -m venv venv

# Активация (Linux/Mac)
source venv/bin/activate

# Активация (Windows)
# venv\Scripts\activate

# Установка зависимостей
pip install -r requirements.txt

# Запуск сервера разработки (миграции выполняются автоматически)
uvicorn app.main:app --reload

# Запуск сервера разработки
uvicorn app.main:app --reload
```

#### Фронтенд

```bash
cd frontend

# Установка зависимостей
npm install

# Запуск сервера разработки
npm start
```

Фронтенд будет доступен по адресу: http://localhost:3000 (или порт, указанный в `FRONTEND_PORT`)

---

## 🗄️ Поддерживаемые базы данных

Приложение поддерживает три типа баз данных:

| База данных | Драйвер | Использование | URL подключения |
|-------------|---------|---------------|-----------------|
| **SQLite** | aiosqlite | Разработка, небольшие проекты | `sqlite+aiosqlite:///./data/app.db` |
| **PostgreSQL** | asyncpg | Production (рекомендуется) | `postgresql+asyncpg://user:pass@host:port/db` |
| **MySQL/MariaDB** | aiomysql | Production (альтернатива) | `mysql+aiomysql://user:pass@host:port/db` |

**Рекомендация:** Используйте PostgreSQL для production-развертывания — он обеспечивает лучшую производительность, поддержку JSON и масштабируемость.

### 🔄 Переключение между базами данных

1. Убедитесь, что нужный драйвер раскомментирован в `backend/requirements.txt`
2. Измените `DATABASE_URL` в файле `.env`
3. Для Docker: раскомментируйте соответствующую службу БД в `docker-compose.yml`
4. **Миграции выполняются автоматически при запуске** — дополнительных действий не требуется

---

## 📁 Структура проекта

```
wowrussian/
├── backend/                    # FastAPI бэкенд
│   ├── app/
│   │   ├── api/               # REST API эндпоинты
│   │   │   ├── auth.py        # Аутентификация
│   │   │   ├── projects.py    # Проекты (анализ сайтов)
│   │   │   ├── pages.py       # Страницы сайтов
│   │   │   ├── stats.py       # Статистика
│   │   │   └── websocket.py   # WebSocket соединения
│   │   ├── core/              # Конфигурация и база данных
│   │   │   ├── config.py      # Настройки приложения
│   │   │   └── database.py    # Подключение к БД
│   │   ├── models/            # SQLAlchemy модели
│   │   │   ├── project.py     # Модель проекта
│   │   │   ├── page.py        # Модель страницы
│   │   │   ├── foreign_word.py # Модель иностранного слова
│   │   │   └── crawl_queue.py # Очередь задач обхода
│   │   ├── schemas/           # Pydantic схемы (валидация)
│   │   ├── services/          # Бизнес-логика
│   │   │   ├── crawler.py     # Парсинг сайтов
│   │   │   ├── analyzer.py    # Анализ текста
│   │   │   ├── parser.py      # Парсинг HTML
│   │   │   └── file_storage.py # Работа с файлами
│   │   └── tasks/             # Celery задачи
│   │       ├── celery_app.py  # Конфигурация Celery
│   │       └── crawl_tasks.py # Задачи обхода сайтов
│   ├── alembic/               # Миграции базы данных
│   ├── Dockerfile
│   ├── requirements.txt
│   └── pytest.ini
│
├── frontend/                   # React фронтенд
│   ├── public/
│   │   └── index.html
│   ├── src/
│   │   ├── pages/             # Компоненты страниц
│   │   │   ├── HomePage.js           # Главная страница
│   │   │   ├── ProjectsListPage.js   # Список проектов
│   │   │   ├── ProjectPage.js        # Детали проекта
│   │   │   └── PageDetailPage.js     # Детали страницы
│   │   ├── services/
│   │   │   └── api.js         # API клиент
│   │   ├── hooks/
│   │   │   └── useWebSocket.js # WebSocket хук
│   │   ├── App.js
│   │   └── index.js
│   ├── Dockerfile
│   ├── nginx.conf
│   └── package.json
│
├── nginx/                      # Nginx конфигурация
│   └── nginx.conf
│
├── docs/                       # Документация
│   ├── API.md                 # Документация API
│   ├── ARCHITECTURE.md        # Архитектура системы
│   ├── DATABASE_MIGRATION.md  # Миграции БД
│   ├── DEPLOYMENT.md          # Развертывание
│   └── DEVELOPMENT.md         # Руководство по разработке
│
├── docker-compose.yml          # Docker Compose конфигурация
├── alembic.ini                 # Конфигурация Alembic
├── .env.example                # Пример переменных окружения
├── .dockerignore
├── .gitignore
└── README.md                   # Английская версия документации
```

---

## 🔌 API Endpoints

### Проекты

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| `POST` | `/api/projects` | Создать новый проект анализа |
| `GET` | `/api/projects` | Получить список проектов пользователя |
| `GET` | `/api/projects/{id}` | Получить детали проекта |
| `DELETE` | `/api/projects/{id}` | Удалить проект |
| `POST` | `/api/projects/{id}/stop` | Остановить анализ |
| `GET` | `/api/projects/{project_id}/pages` | Получить страницы проекта |
| `GET` | `/api/projects/{project_id}/pages/{page_id}` | Получить детали страницы |

### Статистика

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| `GET` | `/api/stats/{project_id}` | Получить статистику проекта |

### Аутентификация

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| `POST` | `/api/auth/register` | Регистрация нового пользователя |
| `POST` | `/api/auth/login` | Вход в систему |
| `POST` | `/api/auth/logout` | Выход из системы |

### WebSocket

Подключитесь к WebSocket для получения обновлений в реальном времени:

```
ws://localhost:8000/ws/projects/{project_id}
```

**Формат сообщений:**

```json
// Анализ начат
{"type": "analysis_started", "project_id": 1}

// Прогресс обхода
{"type": "crawl_progress", "project_id": 1, "current_page": 5, "total_pages": 50}

// Новая страница обработана
{"type": "page_processed", "project_id": 1, "page_id": 10, "url": "https://example.com/page"}

// Анализ завершен
{"type": "analysis_completed", "project_id": 1, "total_words": 1500, "foreign_words": 42}

// Ошибка
{"type": "error", "project_id": 1, "message": "Текст ошибки"}
```

---

## ⚙️ Конфигурация

### Переменные окружения

| Переменная | Описание | Значение по умолчанию |
|------------|----------|----------------------|
| `DEBUG` | Режим отладки | `True` |
| `SECRET_KEY` | Секретный ключ для JWT (обязательно для production!) | `change-me-in-production` |
| `DATABASE_URL` | URL подключения к базе данных | `sqlite+aiosqlite:///./data/app.db` |
| `REDIS_URL` | URL Redis сервера | `redis://redis:6379/0` |
| `STORAGE_PATH` | Путь к хранилищу файлов | `/app/storage` |
| `DICTIONARY_PATH` | Путь к файлу словаря русского языка | `/app/dictionaries/russian_words.txt` |
| `DICTIONARY_URL` | URL для автоматической загрузки словаря | `https://raw.githubusercontent.com/danakt/russian-words/master/russian.txt` |
| `AUTO_DOWNLOAD_DICTIONARY` | Автоматически загружать словарь при отсутствии | `True` |
| **Интеграция 168fz** |||
| `USE_FZ168` | Включить микросервис 168fz для расширенного анализа | `True` |
| `FZ168_URL` | URL адрес сервиса 168fz | `http://fz168:8000` |
| `FZ168_TIMEOUT` | Таймаут запроса к 168fz (секунды) | `10` |
| `FZ168_RETRY_ATTEMPTS` | Количество попыток при ошибке | `3` |
| `CRAWLER_DELAY` | Задержка между запросами (секунды) | `1` |
| `CRAWLER_USER_AGENT` | User-Agent для краулера | `WowRussianBot/1.0` |
| `CRAWLER_TIMEOUT` | Таймаут запросов (секунды) | `30` |
| `CRAWLER_MAX_PAGES` | Максимальное количество страниц для обхода | `1000` |
| `ALLOWED_ORIGINS` | Разрешенные CORS origins (должно включать порт из `FRONTEND_PORT`) | `["http://localhost:3000","http://localhost:8000"]` |

### Примеры URL подключения к БД

**SQLite:**
```env
DATABASE_URL=sqlite+aiosqlite:///./data/app.db
```

**PostgreSQL:**
```env
DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/database_name
```

**MySQL:**
```env
DATABASE_URL=mysql+aiomysql://username:password@localhost:3306/database_name
```

---

## 🔌 Интеграция с 168fz

**WowRussian Analyzer** может интегрироваться с микросервисом [168fz](https://github.com/timophey/168fz) для расширенного анализа текстов на соответствие Федеральному закону №168-ФЗ.

### ✨ Возможности 168fz

- **Расширенная классификация**: обнаружение запрещенных слов, иностранных слов с/без русских аналогов
- **Множество словарей**: использование официальных нормативных словарей и пользовательских словарей
- **Оценка риска**: автоматическое определение уровня риска (низкий/средний/высокий)
- **Определение языка**: идентификация языка иностранных слов

### 🛠️ Настройка

1. **Включите 168fz** в файле `.env`:
   ```env
   USE_FZ168=True
   FZ168_URL=http://fz168:8000  # или адрес внешнего сервера
   ```

2. **Разверните сервис 168fz**:
   - **Вариант A (Docker Compose)**: сервис `fz168` уже настроен в `docker-compose.yml` (включен по умолчанию). Убедитесь, что субмодуль инициализирован.
   - **Вариант B (Внешний)**: разверните 168fz отдельно и укажите его адрес в `FZ168_URL`

3. **Запустите миграции** (выполняются автоматически) - добавляется поле `source` в таблицу `foreign_words`

### 🔄 Поведение при ошибках

Если 168fz недоступен (таймаут, ошибка соединения и т.д.), система автоматически переключается на локальный анализатор. Все операции продолжают работать без прерываний.

### 📊 Отслеживание источника

Поле `source` в таблице `foreign_words` указывает, какой анализатор обнаружил слово:
- `fz168` - обнаружено сервисом 168fz
- `dictionary` - из основного словаря русского языка (локальный fallback)
- `fallback` - из встроенного минимального словаря (локальный fallback)

### ❌ Отключение 168fz

Для использования только локального анализатора:
```env
USE_FZ168=False
```

---

## 🧪 Тестирование

### Запуск тестов

```bash
cd backend
pytest
```

### Покрытие кода

```bash
cd backend
pytest --cov=app --cov-report=html
```

---

## 🗃️ Миграции базы данных

**Важно:** Миграции выполняются автоматически при запуске приложения.

### Создание новой миграции

```bash
cd backend
alembic revision --autogenerate -m "Описание миграции"
```

### Ручное управление миграциями (для отладки)

Применить миграции вручную:
```bash
cd backend
alembic upgrade head
```

Откатить последнюю миграцию:
```bash
cd backend
alembic downgrade -1
```

---

## 📚 Дополнительная документация

- **[API Documentation](docs/API.md)** (англ.) — Полное описание REST API endpoints
- **[Architecture](docs/ARCHITECTURE.md)** (англ.) — Архитектурные решения и диаграммы
- **[Database Migration](docs/DATABASE_MIGRATION.md)** (англ.) — Подробное руководство по миграциям
- **[Deployment](docs/DEPLOYMENT.md)** (англ.) — Инструкции по развертыванию на сервере
- **[Development](docs/DEVELOPMENT.md)** (англ.) — Руководство для разработчиков

---

## 🔧 Развертывание на сервере

Подробные инструкции по развертыванию на VPS с использованием CloudPanel или вручную:

**[📖 DEPLOYMENT.md](docs/DEPLOYMENT.md)**

---

## 🤝 Вклад в проект

Мы открыты для вкладов! Пожалуйста, следуйте этим шагам:

1. **Fork** репозитория
2. Создайте **feature branch**: `git checkout -b feature/AmazingFeature`
3. **Commit** изменения: `git commit -m 'Add: AmazingFeature'`
4. **Push** в ветку: `git push origin feature/AmazingFeature`
5. Откройте **Pull Request**

### Стандарты кода

- Следуйте PEP 8 для Python кода
- Используйте type hints
- Пишите тесты для новых функций
- Обновляйте документацию при изменении API

---

## 📄 Лицензия

MIT License. См. файл [LICENSE](LICENSE) для подробностей.

---

## 📞 Поддержка

Если у вас возникли проблемы или вопросы:

1. Проверьте [документацию](docs/)
2. Поищите в [Issues](../../issues)
3. Создайте новый Issue с подробным описанием проблемы

---

## 🙏 Благодарности

- [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) — для парсинга HTML
- [FastAPI](https://fastapi.tiangolo.com/) — фреймворк для API
- [React](https://reactjs.org/) — библиотека для UI
- [Material-UI](https://mui.com/) — компоненты интерфейса
- [Celery](https://docs.celeryq.dev/) — асинхронные задачи
- [Russian Words Dictionary](https://github.com/danakt/russian-words) — словарь русского языка

---

## 📦 Git Submodules

Этот репозиторий использует git submodules для микросервиса 168fz.

### Клонирование

Клонировать с субмодулями:
```bash
git clone --recurse-submodules https://github.com/timophey/wowrussian.git
cd wowrussian
```

Или инициализировать после клонирования:
```bash
git submodule update --init --recursive
```

### Обновление субмодуля

Чтобы обновить субмодуль 168fz до последней версии:

```bash
cd 168fz
git pull origin master
cd ..
git add 168fz

---

## 🔒 Соответствие 152-ФЗ (Федеральный закон "О персональных данных")

Приложение разработано с учётом требований Федерального закона № 152-ФЗ "О персональных данных". Реализованы следующие меры:

### Реализованные меры соответствия

| Функция | Описание |
|---------|----------|
| **Политика конфиденциальности** | Доступна на странице `/privacy-policy` |
| **Согласие на cookies** | Баннер при первом посещении с кнопками Принять/Отклонить |
| **Согласие на обработку данных** | Чекбокс обязателен при регистрации |
| **Право на удаление** | Пользователи могут удалить аккаунт и связанные данные |
| **Информация об операторе** | Отображается в футере и доступна через `/api/auth/legal-info` |

### Собираемые персональные данные

- Адрес электронной почты (для аутентификации)
- Хэш пароля (bcrypt, пароли не хранятся в открытом виде)
- IP-адрес (для гостевых сессий)
- User-Agent браузера (для гостевых сессий)
- Данные сессий
- Данные анализа веб-сайтов (URL, содержимое страниц)

### API эндпоинты для реализации прав на данные

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| `POST` | `/api/auth/me/delete-account` | Удалить аккаунт авторизованного пользователя |
| `POST` | `/api/auth/guest/delete-session` | Удалить гостевую сессию и данные |
| `GET` | `/api/auth/legal-info` | Получить юридическую информацию об операторе |

### Миграция базы данных

Выполните следующую команду для применения миграции для соответствия 152-ФЗ:

```bash
cd backend
alembic upgrade head
```

### Настройка для production

Для production-развёртывания убедитесь, что вы:

1. Обновили информацию об операторе в [`Footer.js`](frontend/src/components/Footer.js) и [`auth.py`](backend/app/api/auth.py)
2. Установили правильный URL политики конфиденциальности
3. Настроили HTTPS для безопасной передачи данных
4. Проверили и обновили содержание политики конфиденциальности в [`PrivacyPolicyPage.js`](frontend/src/pages/PrivacyPolicyPage.js)
git commit -m "Update 168fz submodule to latest version"
git push
```

### Развертывание с субмодулями

На сервере развертывания после `git pull` всегда выполняйте:

```bash
git submodule update --init --recursive
```

Или используйте предоставленные скрипты развертывания, которые автоматически обрабатывают субмодули.

---

**⭐ Если этот проект полезен, поставьте звезду! ⭐**