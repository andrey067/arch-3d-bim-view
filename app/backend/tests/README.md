# Backend Tests

## Stack

- **pytest** 8.3+ with `pytest-cov` for coverage
- **SQLite in-memory** for test isolation (no external DB needed)
- **FastAPI TestClient** for HTTP integration tests
- **Celery eager mode** (`CELERY_TASK_ALWAYS_EAGER=true`) for synchronous task execution

## Fixtures

| Fixture | Scope | Description |
|---------|-------|-------------|
| `db_engine` | function | Fresh in-memory SQLite engine per test |
| `db_session` | function | Rolled-back session (savepoint isolation) |
| `client` | function | `TestClient` with DB override |
| `tmp_storage` | function | Temporary storage directory |
| `celery_eager` | function (autouse) | Forces Celery sync mode |

## Running

```bash
# All tests
python -m pytest tests/ -v

# With coverage
python -m pytest tests/ --cov=app --cov-report=term-missing

# Single file
python -m pytest tests/test_auth.py -v

# Single test
python -m pytest tests/test_auth.py::test_register_success -v
```

## Structure

| File | Feature | Tests |
|------|---------|-------|
| `test_health.py` | Health + correlation | 4 |
| `test_config.py` | Settings | 3 |
| `test_security_password.py` | Password hashing | 1 |
| `test_detection.py` | Magic bytes detection | 15 |
| `test_auth.py` | Auth (register/login/refresh/logout/me) | 15 |
| `test_projects.py` | Project CRUD | 11 |
| `test_upload.py` | File upload/list/delete | 13 |
| `test_conversion.py` | Jobs, retry, pipeline dispatch, service | 17 |
| `test_sharing.py` | Share links + public viewer | 19 |
| `test_viewer.py` | Viewer endpoints + thumbnail pipeline | 11 |
| `test_storage.py` | LocalDiskStorage + key builders | 17 |

## Conventions

- Each test is independent (no shared state between tests)
- Use `_register_and_login(client)` helper for auth setup
- Use `_create_project(client, token)` helper for project setup
- Mock Blender/subprocess in pipeline tests (no real Blender in CI)
- Storage tests use `tmp_path` fixture (no real filesystem side effects)
