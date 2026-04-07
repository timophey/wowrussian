"""seed static pages with privacy-policy and legal-info

Revision ID: 015
Revises: 014
Create Date: 2026-04-07 12:35:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = '015'
down_revision = '014'
branch_labels = None
depends_on = None

# Initial content in Russian and English
PRIVACY_POLICY_RU = """# Политика конфиденциальности

**Дата последнего обновления:** {date}

## 1. Общие положения

Настоящая Политика конфиденциальности определяет порядок обработки и защиты персональных данных пользователей сервиса WowRussian Анализатор. Оператор обеспечивает защиту обрабатываемых персональных данных от несанкционированного доступа и разглашения в соответствии с Федеральным законом от 27.07.2006 № 152-ФЗ «О персональных данных».

## 2. Оператор персональных данных

Оператором персональных данных является администрация сервиса WowRussian Анализатор. Адрес для связи: privacy@wowrussian.ru

## 3. Собираемые персональные данные

Мы собираем и обрабатываем следующие категории персональных данных:

- Адрес электронной почты
- Хэш пароля (мы не храним пароли в открытом виде)
- IP-адрес (для гостевых сессий)
- User-Agent браузера (для гостевых сессий)
- Данные сессий
- Данные анализа веб-сайтов (URL, содержимое страниц)

## 4. Цели обработки данных

Персональные данные обрабатываются в следующих целях:

- Аутентификация и предоставление доступа к сервису
- Предоставление услуг анализа веб-сайтов
- Улучшение качества сервиса
- Обеспечение безопасности и предотвращение мошенничества

## 5. Правовые основания обработки

Обработка персональных данных осуществляется на основании:

- Согласия субъекта персональных данных (при регистрации)
- Необходимости исполнения договора (пользовательского соглашения)
- Законного интереса оператора (улучшение сервиса, безопасность)

## 6. Сроки хранения

Персональные данные хранятся не дольше, чем это необходимо для целей их обработки, если иное не установлено законодательством РФ. Пользователь может запросить удаление своих данных в любое время.

## 7. Права субъекта персональных данных

В соответствии с Федеральным законом № 152-ФЗ, вы имеете право:

- На доступ к своим персонаальным данным
- На уточнение и исправление неточных данных
- На удаление персональных данных
- На ограничение обработки данных
- На переносимость данных
- На возражение против обработки
- На обращение в Роскомнадзор для защиты своих прав

## 8. Использование файлов cookie

Мы используем файлы cookie для обеспечения работоспособности сервиса, аутентификации и анализа использования сайта. Продолжая использовать сайт, вы соглашаетесь на использование файлов cookie.

## 9. Передача данных третьим лицам

Мы не передаем ваши персональные данные третьим лицам, за исключением случаев, предусмотренных законодательством РФ или необходимых для предоставления услуг (например, хостинг-провайдеру).

## 10. Защита данных

Мы принимаем необходимые организационные и технические меры для защиты персональных данных от несанкционированного доступа, утраты, изменения, блокирования, копирования, распространения.

## 11. Изменения в политике

Мы оставляем за собой право вносить изменения в настоящую Политику конфиденциальности. Актуальная версия всегда доступна на этой странице.

## 12. Контактная информация

По всем вопросам, связанным с обработкой персональных данных, вы можете связаться с нами:

**Email:** privacy@wowrussian.ru
"""

PRIVACY_POLICY_EN = """# Privacy Policy

**Last updated:** {date}

## 1. General Provisions

This Privacy Policy defines the procedure for processing and protecting personal data of users of the WowRussian Analyzer service. The operator ensures protection of processed personal data from unauthorized access and disclosure in accordance with Federal Law No. 152-FZ dated July 27, 2006 "On Personal Data".

## 2. Personal Data Operator

The personal data operator is the administration of the WowRussian Analyzer service. Contact address: privacy@wowrussian.ru

## 3. Collected Personal Data

We collect and process the following categories of personal data:

- Email address
- Password hash (we do not store passwords in plain text)
- IP address (for guest sessions)
- Browser User-Agent (for guest sessions)
- Session data
- Website analysis data (URLs, page content)

## 4. Purposes of Data Processing

Personal data is processed for the following purposes:

- Authentication and providing access to the service
- Providing website analysis services
- Improving service quality
- Ensuring security and preventing fraud

## 5. Legal Basis for Processing

Personal data processing is based on:

- Consent of the personal data subject (upon registration)
- Necessity of contract performance (user agreement)
- Legitimate interest of the operator (service improvement, security)

## 6. Storage Periods

Personal data is stored no longer than necessary for the purposes of processing, unless otherwise established by the legislation of the Russian Federation. The user may request deletion of their data at any time.

## 7. Rights of the Personal Data Subject

In accordance with Federal Law No. 152-FZ, you have the right to:

- Access your personal data
- Correct inaccurate data
- Delete personal data
- Restrict data processing
- Data portability
- Object to processing
- File a complaint with Roskomnadzor to protect your rights

## 8. Use of Cookies

We use cookies to ensure service functionality, authentication, and analyze site usage. By continuing to use the site, you consent to the use of cookies.

## 9. Transfer to Third Parties

We do not transfer your personal data to third parties, except as provided by the legislation of the Russian Federation or necessary for providing services (e.g., to a hosting provider).

## 10. Data Security

We take necessary organizational and technical measures to protect personal data from unauthorized access, loss, alteration, blocking, copying, and distribution.

## 11. Changes to the Policy

We reserve the right to make changes to this Privacy Policy. The current version is always available on this page.

## 12. Contact Information

For any questions related to personal data processing, you can contact us:

**Email:** privacy@wowrussian.ru
"""

LEGAL_INFO_RU = """# Правовая информация

## Информация об операторе

Данные оператора предоставляются в соответствии с Федеральным законом № 152-ФЗ «О персональных данных».

Для получения актуальной информации об операторе свяжитесь с нами по адресу: privacy@wowrussian.ru

## Отказ от ответственности

### Сервис предоставляется «как есть»

Сервис предоставляется без гарантий бесперебойной работы, безопасности или точности результатов. Мы не гарантируем полную точность определения иностранных слов и соответствие всем требованиям законодательства.

### Не является юридической консультацией

Результаты анализа 168-ФЗ носят информационный характер и не являются юридическим заключением. Для официальных вопросов, связанных с соответствием законодательству, обращайтесь к квалифицированным юристам.

### Ограничение ответственности

Оператор не несёт ответственности за решения, принятые на основе результатов анализа сервиса. Использование сервиса осуществляется на ваш собственный риск.

### Цель сбора персональных данных

Персональные данные собираются исключительно для функционирования сервиса (аутентификация, хранение проектов). Данные не продаются и не передаются третьим лицам, за исключением случаев, предусмотренных законодательством РФ.

### Cookies и аналитика

Мы используем файлы cookie для обеспечения работоспособности сервиса, аутентификации и анализа использования сайта. Вы можете управлять настройками cookies в вашем браузере.

## Законодательная база

Обработка персональных данных осуществляется в соответствии с Федеральным законом от 27.07.2006 № 152-ФЗ «О персональных данных».

---

См. также: [Политика конфиденциальности](/privacy-policy)
"""

LEGAL_INFO_EN = """# Legal Information

## Operator Information

Operator data is provided in accordance with Federal Law No. 152-FZ "On Personal Data".

For current operator information, contact us at: privacy@wowrussian.ru

## Disclaimer

### Service Provided "As Is"

The service is provided without guarantees of uninterrupted operation, security, or accuracy of results. We do not guarantee complete accuracy of foreign word detection and compliance with all legislative requirements.

### Not Legal Advice

The results of 168-FZ analysis are for informational purposes only and do not constitute a legal opinion. For official questions related to legislative compliance, consult qualified lawyers.

### Limitation of Liability

The operator is not responsible for decisions made based on the service analysis results. Use of the service is at your own risk.

### Purpose of Collecting Personal Data

Personal data is collected solely for the functioning of the service (authentication, project storage). Data is not sold or transferred to third parties, except as provided by the legislation of the Russian Federation.

### Cookies and Analytics

We use cookies to ensure service functionality, authentication, and analyze site usage. You can manage cookie settings in your browser.

## Legislative Framework

Personal data processing is carried out in accordance with Federal Law No. 152-FZ dated July 27, 2006 "On Personal Data".

---

See also: [Privacy Policy](/privacy-policy)
"""


def upgrade() -> None:
    # Table already exists in migration 014
    # Just insert seed data
    conn = op.get_bind()
    metadata = sa.MetaData()
    static_pages = sa.Table(
        'static_pages',
        metadata,
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('url', sa.String(), nullable=False),
        sa.Column('lang', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('content_md', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    now = datetime.utcnow()
    date_str = now.strftime('%d.%m.%Y')

    # Insert seed data
    conn.execute(static_pages.insert(), [
        {
            'url': 'privacy-policy',
            'lang': 'ru',
            'title': 'Политика конфиденциальности',
            'content_md': PRIVACY_POLICY_RU.format(date=date_str),
            'created_at': now,
            'updated_at': now,
        },
        {
            'url': 'privacy-policy',
            'lang': 'en',
            'title': 'Privacy Policy',
            'content_md': PRIVACY_POLICY_EN.format(date=date_str),
            'created_at': now,
            'updated_at': now,
        },
        {
            'url': 'legal-info',
            'lang': 'ru',
            'title': 'Правовая информация',
            'content_md': LEGAL_INFO_RU,
            'created_at': now,
            'updated_at': now,
        },
        {
            'url': 'legal-info',
            'lang': 'en',
            'title': 'Legal Information',
            'content_md': LEGAL_INFO_EN,
            'created_at': now,
            'updated_at': now,
        },
    ])


def downgrade() -> None:
    # Remove seed data only (table is dropped in 014)
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM static_pages WHERE url IN ('privacy-policy', 'legal-info')")
    )
