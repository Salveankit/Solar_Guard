# Database Migrations

SolarGuard uses Alembic for the Neon/PostgreSQL schema.

Set the target URL explicitly when running migrations. Alembic intentionally refuses to use
the placeholder URL in `alembic.ini`.

```powershell
$env:DATABASE_URL = "<presentation Neon URL>"
uv run alembic -x database_url=$env:DATABASE_URL upgrade head
```

For integration tests, use the Neon test branch/database only:

```powershell
$env:TEST_DATABASE_URL = "<test Neon URL>"
uv run alembic -x database_url=$env:TEST_DATABASE_URL upgrade head
```

Automated tests must not run against the presentation database.

Verification commands should always use `TEST_DATABASE_URL`:

```powershell
uv run alembic -x database_url=$env:TEST_DATABASE_URL upgrade head
uv run alembic -x database_url=$env:TEST_DATABASE_URL current
```
