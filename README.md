# Account API

FastAPI, PostgreSQL, SQLAlchemy AsyncSession через **asyncpg**, Alembic, JWT и Argon2.
Python 3.12+; локально проверено на Python 3.14.

```text
app/
  api/
    account.py             # POST /account/register и POST /account/token
    dependencies.py        # Сессия БД и внедрение сервиса
  bll/
    account_service.py     # Регистрация, проверка пароля, выдача JWT
  dal/
    account_repository.py  # Запросы к PostgreSQL и транзакции
  models/
    base.py                # DeclarativeBase
    user.py                # ORM-модель User
    __init__.py            # Экспорт Base и моделей для Alembic
  main.py                  # Точка входа, сборка приложения
config/
  settings.py              # Настройки .env, async engine и session factory
alembic/
  env.py                   # Импорт Base из app.models, async-миграции
  versions/
    0001_create_users.py    # Начальная миграция
tests/
  test_account_api.py
  test_account_service.py
  test_account_repository.py
  test_postgres.py          # Интеграционный тест настоящего PostgreSQL
```

API вызывает BLL; сервис работает через интерфейс хранилища; DAL реализует
этот интерфейс и обращается к ORM. SQL-запросы находятся в DAL. HTTP-ошибки
формируются в API. Пароли сохраняются только в виде Argon2-хешей.
Имена пользователей нечувствительны к регистру, уникальность защищена также в БД.
Файл репозитория назван `account_repository.py`, чтобы использовать обычный импорт Python.

## Установка

```powershell
python -m pip install --user poetry
python -m poetry install
```

Для запуска без тестовых пакетов: `python -m poetry install --only main`.

Зависимости описаны в `pyproject.toml`, точные версии фиксируются в `poetry.lock`.
Poetry автоматически управляет окружением `.venv`; создавать и активировать его
вручную не нужно. Файл `poetry.lock` следует хранить в Git.

Добавить пакет: `python -m poetry add package-name`.
Добавить тестовую зависимость: `python -m poetry add --group dev package-name`.

## Настройки и запуск

В рабочей папке уже создан локальный `.env` со случайным JWT-секретом.
При новом клонировании скопируйте `.env.example` в `.env`, задайте адрес своей БД
и замените `JWT_SECRET_KEY` случайным значением:

```powershell
python -m poetry run python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Для PostgreSQL из `compose.yaml` нужен запущенный Docker Desktop:

```powershell
docker compose up -d --wait
python -m poetry run alembic upgrade head
python -m poetry run uvicorn app.main:app --reload
```

Swagger UI: http://127.0.0.1:8000/docs

Таблицы создаются миграциями; приложение не вызывает `create_all` при запуске.
`DATABASE_URL` использует формат `postgresql+asyncpg://user:password@host:5432/database`.
JWT подписывается HS256; срок жизни задаётся `ACCESS_TOKEN_EXPIRE_MINUTES`.

## Два эндпоинта

Регистрация — JSON, ответ 201 с `id` и `username`:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/account/register -ContentType application/json -Body '{"username":"alice","password":"strong-password"}'
```

Получение JWT — form-urlencoded, ответ с `access_token` и `token_type=bearer`:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/account/token -ContentType application/x-www-form-urlencoded -Body @{username="alice"; password="strong-password"}
```

Повторная регистрация возвращает 409, неправильный логин/пароль — 401,
некорректные входные данные — 422. Пароль и его хеш не входят в ответы.
Имя: 3–50 латинских букв, цифр или `_`; пароль: 8–128 символов.

## Тесты

```powershell
python -m poetry run pytest
python -m poetry run pytest --cov=app --cov=config --cov-report=term-missing --junitxml=report.xml
```

Обычные тесты API/BLL используют подмену репозитория без подключения к БД.
Тесты DAL отдельно проверяют откат транзакций. SQLite не используется.

Для проверки запросов DAL на настоящем PostgreSQL:

```powershell
$env:TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/accounts"
python -m poetry run pytest -m integration
```

Этот тест создаёт уникальную временную схему и удаляет её после проверки;
учётной записи нужны права создания схем. Без `TEST_DATABASE_URL` он пропускается.
Для будущего CI задайте эту переменную и поднимите сервис PostgreSQL.

## Новые миграции

Добавьте ORM-модель в `app/models/` и импортируйте её в `app/models/__init__.py`:

```powershell
python -m poetry run alembic revision --autogenerate -m "describe change"
python -m poetry run alembic upgrade head
```

Перед применением проверяйте сгенерированную миграцию.
