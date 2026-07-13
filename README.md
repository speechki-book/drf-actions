# drf-actions

Create event log with help triggers and send notify after create event

## Requirements

- Python 3.10+
- Django 4.2 / 5.x (5.2 LTS is the primary target)
- PostgreSQL (the event journal is populated by native PG triggers)

## Development

```bash
docker run -d --name drf-actions-test-pg \
  -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=drf_actions \
  -p 54329:5432 postgres:16-alpine
uv venv --python 3.13 .venv
uv pip install --python .venv/bin/python -e . pytest pytest-django "psycopg[binary]"
.venv/bin/python -m pytest
```
