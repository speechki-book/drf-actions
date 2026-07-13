# drf-actions

[![PyPI](https://img.shields.io/pypi/v/drf-actions)](https://pypi.org/project/drf-actions/)
[![Python versions](https://img.shields.io/pypi/pyversions/drf-actions)](https://pypi.org/project/drf-actions/)
[![Django](https://img.shields.io/badge/django-4.2%20%7C%205.2-0C4B33)](https://pypi.org/project/drf-actions/)
[![Tests](https://github.com/speechki-book/drf-actions/actions/workflows/tests.yml/badge.svg)](https://github.com/speechki-book/drf-actions/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/speechki-book/drf-actions/blob/master/LICENSE)

Django app that keeps an **event journal** of row changes (`INSERT` / `UPDATE` / `DELETE`) for selected models using **native PostgreSQL triggers**, and exposes the journal through a read-only **Django REST Framework** API.

Because the journal is populated by database triggers (not Django signals), it captures every change — including raw SQL, `bulk_update`, and writes from other services sharing the same database.

## How it works

1. You describe which models (tables) to watch in the `DRF_ACTIONS_SETTINGS` setting.
2. For each watched model you create an `ActionContentType` record. On save, the app generates a PL/pgSQL function and an `AFTER INSERT OR UPDATE OR DELETE` trigger on the table.
3. Every change to the table inserts a row into the `EventJournal` table with the reason (`INSERT` / `UPDATE` / `DELETE`), the object id and a JSON snapshot of the configured fields.
4. Consumers read the journal via the REST endpoint (protected by [API keys](https://florimondmanca.github.io/djangorestframework-api-key/)) or directly via the ORM.

## Requirements

- Python 3.10+
- Django 4.2 / 5.x (5.2 LTS is the primary target)
- Django REST Framework 3.16+
- PostgreSQL (the event journal is populated by native PG triggers)

## Installation

```bash
pip install drf-actions
```

Add the app and its dependencies to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    # ...
    "rest_framework",
    "rest_framework_api_key",
    "django_filters",
    "django_json_widget",  # nicer JSON display in the admin
    "drf_actions",
]
```

Run the migrations:

```bash
python manage.py migrate drf_actions
```

## Configuration

Describe the models you want to track with `DRF_ACTIONS_SETTINGS` in your Django settings:

```python
DRF_ACTIONS_SETTINGS = {
    "content_types": {
        "user": {
            # primary key field of the watched table
            "pk": "id",
            # optional: column whose value is stored as "owner" in the event data
            "owner": None,
            # optional: fire UPDATE events only when these columns change
            "catch_update": [],
            # optional: many-to-many relations to embed into the event data
            "m2m": [
                # (through_table, fk_to_related, fk_to_this,
                #  related_table, related_pk, related_column, json_key)
                ("users_user_groups", "group_id", "user_id",
                 "auth_group", "id", "name", "groups"),
            ],
            # (app_label, model_name) of the watched model
            "model": ("users", "user"),
            # columns to snapshot: (json_key, table_column)
            "fields": (
                ("email", "email"),
                ("full_name", "full_name"),
            ),
        },
    },
    # backfill events for rows that already exist when a trigger is installed
    "create_event_for_new_entity": True,
}
```

### Content type options

| Key | Required | Description |
| --- | --- | --- |
| `pk` | yes | Name of the primary key column of the watched table. |
| `model` | yes | `(app_label, model_name)` tuple used to resolve the Django model. |
| `fields` | yes | Iterable of `(json_key, table_column)` pairs snapshotted into `EventJournal.data`. |
| `owner` | no | Column stored as `owner` in the event data (e.g. to route notifications). |
| `catch_update` | no | List of columns; when set, `UPDATE` events fire only if one of them changes. |
| `m2m` | no | Many-to-many relations aggregated into the event data (see the tuple layout above). |

### Installing the triggers

Create an `ActionContentType` for each configured content type — the PostgreSQL function and trigger are created automatically on save:

```python
from drf_actions.models import ActionContentType

ActionContentType.objects.create(content_type="user", table="users_user")
```

If `create_event_for_new_entity` is `True`, existing rows are backfilled into the journal as `INSERT` events at that moment. Deleting an `ActionContentType` drops the trigger and its function.

## REST API

Hook up the bundled router:

```python
# urls.py
from django.urls import include, path

urlpatterns = [
    # ...
    path("api/", include("drf_actions.urls")),
]
```

This exposes a read-only endpoint at `api/actions/events/`, protected with `rest_framework_api_key` (send `Authorization: Api-Key <key>`).

Supported query parameters:

- filtering: `id`, `id__in`, `id__lt/lte/gt/gte`, `created__range/lt/lte/gt/gte`, `reason`, `reason__in`, `content_type`, `content_type__in`
- ordering: `ordering=id`, `ordering=-created`
- pagination: `page`, `page_size` (default 100, max 10000)

Example response item:

```json
{
    "id": 42,
    "reason": "UPDATE",
    "object_id": "7",
    "content_type": "user",
    "data": {"email": "user@example.com", "full_name": "Jane Doe", "groups": ["editors"]},
    "created": "2026-07-13T12:00:00Z",
    "modified": "2026-07-13T12:00:00Z"
}
```

## Development

```bash
docker run -d --name drf-actions-test-pg \
  -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=drf_actions \
  -p 54329:5432 postgres:16-alpine
uv venv --python 3.13 .venv
uv pip install --python .venv/bin/python -e . pytest pytest-django "psycopg[binary]"
.venv/bin/python -m pytest
```

## License

[MIT](https://github.com/speechki-book/drf-actions/blob/master/LICENSE)
