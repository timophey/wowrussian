# Data Attributes Guide

Этот документ описывает соглашение по использованию `data-block` атрибутов во фронтенде для удобной идентификации блоков в DevTools.

## Purpose

Data-атрибуты позволяют быстро находить и идентифицировать элементы вёрстки в браузерных DevTools, что особенно полезно при:
- Обсуждении вёрстки в чате/коммуникации
- Отладке и тестировании
- Написании e2e-тестов
- Быстрой навигации по DOM-структуре

## Convention

Используем атрибут `data-block` с понятными именами на английском языке в kebab-case:

```jsx
<div data-block="header">...</div>
<Button data-block="submit-button">Submit</Button>
```

## Existing Data Blocks

### App.js
- `header` - верхняя панель с настройками и авторизацией
- `main-container` - основной контейнер с роутингом

### Pages

#### HomePage
- `home-container` - контейнер домашней страницы
- `home-content` - основной контент
- `url-form` - форма ввода URL
- `analyze-button` - кнопка запуска анализа
- `home-description` - описание на главной

#### ProjectsListPage
- `projects-list-container` - контейнер списка проектов
- `projects-header` - заголовок с кнопкой создания
- `new-analysis-button` - кнопка "Новый анализ"
- `projects-table` - таблица проектов

#### ProjectPage
- `project-container` - контейнер страницы проекта
- `project-header` - заголовок проекта с навигацией
- `project-stats` - сетка статистики
- `stat-card-total-pages` - карточка "Всего страниц"
- `stat-card-foreign-words` - карточка "Иностранных слов"
- `stat-card-unique-foreign` - карточка "Уникальных иностранных"
- `stat-card-foreign-percent` - карточка "Процент иностранных"
- `project-actions` - панель действий
- `start-download-button` - кнопка "Запустить сканирование"
- `stop-button` - кнопка "Остановить"
- `clear-pages-button` - кнопка "Очистить страницы"
- `pages-table` - таблица страниц проекта

#### PageDetailPage
- `page-detail-container` - контейнер деталей страницы
- `page-detail-header` - заголовок с навигацией
- `page-status-badge` - статус страницы
- `page-stats` - статистика страницы
- `view-buttons` - кнопки просмотра HTML/Text
- `view-html-button` - кнопка "Просмотр HTML"
- `view-text-button` - кнопка "Просмотр текста"
- `foreign-words-table` - таблица иностранных слов
- `russian-words-table` - таблица русских слов
- `fz168-section` - раздел 168-ФЗ
- `fz168-summary-accordion` - аккордеон "Сводка"
- `fz168-summary-card-*` - карточки сводки
- `fz168-checks-accordion` - аккордеон "Проверки"
- `fz168-statistics-accordion` - аккордеон "Статистика"
- `fz168-dictionaries-accordion` - аккордеон "Словари"
- `html-dialog` - диалог HTML
- `text-dialog` - диалог текста

#### SinglePage
- `single-page-container` - контейнер одиночного анализа
- `single-page-header` - заголовок страницы
- `single-analysis-form` - форма анализа
- `url-input` - поле ввода URL
- `form-buttons` - кнопки формы
- `analyze-button` - кнопка "Анализировать"
- `clear-button` - кнопка "Очистить"
- `download-button` - кнопка "Скачать JSON"

#### AdminPage
- `admin-login-container` - контейнер входа админа
- `admin-login-form` - форма входа
- `admin-key-input` - поле ввода ключа
- `login-button` - кнопка "Войти"
- `admin-panel-container` - контейнер панели админа
- `admin-panel-header` - заголовок панели
- `create-user-button` - кнопка "Создать пользователя"
- `back-to-projects-button` - кнопка "Назад к проектам"
- `logout-button` - кнопка "Выйти"
- `users-table` - таблица пользователей
- `create-user-dialog` - диалог создания пользователя

### Components

#### AnalysisResults
- `source-info` - информация об источнике
- `stats-grid` - сетка статистики
- `stat-card-total-words` - карточка "Всего слов"
- `stat-card-unique-words` - карточка "Уникальных слов"
- `stat-card-risk-level` - карточка "Уровень риска"
- `stat-card-violations` - карточка "Нарушений"
- `status-summary` - сводка по статусам
- `words-table-paper` - бумага таблицы слов
- `words-table-header` - заголовок таблицы
- `word-filter-input` - поле фильтра слов
- `words-table` - таблица всех слов
- `summary-accordion` - аккордеон "Сводка"
- `checks-accordion` - аккордеон "Проверки"
- `prohibited-words-section` - секция запрещенных слов
- `foreign-words-section` - секция иностранных слов
- `normative-violations-section` - секция нарушений норм
- `recommendations-section` - секция рекомендаций
- `statistics-accordion` - аккордеон "Статистика"

## Guidelines for Future Development

### When to Add Data Attributes
- **Всегда** для контейнеров страниц (Page-level components)
- **Всегда** для основных секций (headers, forms, tables, action panels)
- **Всегда** для кнопок действий (особенно если их несколько в одной панели)
- **Всегда** для диалогов и модальных окон
- **Всегда** для аккордеонов и сложных компонентов

### Naming Rules
1. Используйте kebab-case: `my-block-name`
2. Имена должны быть понятными и отражать назначение блока
3. Избегайте общих имен типа `container`, `box` - уточняйте: `stats-container`, `form-box`
4. Для повторяющихся элементов используйте общий префикс: `stat-card-*`, `button-*`
5. Для таблиц: `[entity]-table` (projects-table, users-table)
6. Для форм: `[action]-form` (login-form, search-form)
7. Для диалогов: `[purpose]-dialog` (create-user-dialog, html-dialog)

### Consistency
- Проверяйте существующие имена перед добавлением новых
- Следуйте существующим паттернам (например, `*-button` для кнопок)
- Не меняйте существующие имена без необходимости

## Quick Reference

При добавлении нового компонента/блока:
1. Определите его назначение
2. Выберите подходящее имя по соглашению
3. Добавьте `data-block="block-name"` на корневой элемент
4. Обновите этот документ

## Benefits

- **Быстрая навигация**: В DevTools можно искать по `[data-block="projects-table"]`
- **Четкая коммуникация**: "Проблема в `data-block='analyze-button'`" вместо "кнопка где-то в форме"
- **Тестирование**: Легко селектить элементы для e2e-тестов
- **Документация**: Атрибуты сами документируют структуру

---

**Last Updated**: 2025-03-30
**Version**: 1.0