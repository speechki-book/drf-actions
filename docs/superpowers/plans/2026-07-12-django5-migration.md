# SPB-1354: drf-actions Django 5 Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the `drf-actions` library from Django 3.2 to Django 5.2 LTS (keeping Django 4.2 installable for staged host-project migration), with a test harness that proves the Postgres-trigger core actually works.

**Architecture:** `drf-actions` is a small reusable Django app: an `EventJournal` model populated by PostgreSQL triggers (created via raw SQL from `ActionContentType`), exposed through a read-only DRF viewset. The migration is mostly dependency/metadata work plus one hard breakage (a removed Django import in a historical migration). Because the core is raw plpgsql, verification requires a real PostgreSQL — the plan adds a minimal pytest-django harness with a dockerized Postgres and a CI workflow.

**Tech Stack:** Python 3.10–3.13, Django >=4.2,<6.0 (primary target 5.2 LTS), DRF >=3.16, django-filter >=24.3, django-model-utils >=5.0.0, djangorestframework-api-key, django-json-widget, pytest + pytest-django + psycopg 3, Poetry (build backend; run via `uvx poetry`), uv for the dev venv, Docker for Postgres.

---

## Why these changes (breaking-change inventory)

| # | Problem | Where | Fix |
|---|---------|-------|-----|
| 1 | `django.contrib.postgres.fields.jsonb.JSONField` is a **removed-API compat shim** — it still importable in Django 4.2/5.2/6.0 solely to keep historical migrations loading (`system_check_removed_details`, fields.E904), so nothing crashes today, but it is dead API that upstream tells you to migrate off | `drf_actions/migrations/0001_initial.py:3,107` | Rewrite the historical migration to use `models.JSONField` (equivalent since Django 3.1; same `jsonb` column — safe to edit in place, no-op for deployed DBs) |
| 2 | Dependency pins predate Django 5 (`Django>=3.2.14`, DRF 3.12, django-filter 22.1, model-utils 4.1, Python `^3.7`) | `pyproject.toml` | Bump ranges (see Task 1 table) |
| 3 | `rest_framework_api_key` and `django_json_widget` are hard-imported but **not declared** as dependencies | `drf_actions/views/event_journal.py:3`, `drf_actions/admin.py:3` | Declare `djangorestframework-api-key>=3.1.0`, `django-json-widget>=2.0.0` |
| 4 | No `default_auto_field` on the AppConfig — host projects on Django ≥4 without a global `DEFAULT_AUTO_FIELD` get warning W042 / spurious migrations (migration 0003 already uses `BigAutoField`) | `drf_actions/apps.py` | Set `default_auto_field = "django.db.models.BigAutoField"` |
| 5 | Zero tests — no way to prove the migration works | — | Add pytest-django harness + Postgres trigger integration tests + CI |
| 6 | Tooling rot: pre-commit pins (`black rev: stable` no longer resolves), publish workflow uses `checkout@v2` | `.pre-commit-config.yaml`, `.github/workflows/publish.yml` | Modernize pins |

`model_utils.Choices` is still available (not removed) in django-model-utils 5.0.0 — no code change needed there.

## Pre-existing bugs — explicitly OUT OF SCOPE (do not fix, do not "improve")

These exist on master today and are unrelated to Django 5. Leave the behavior byte-identical; file follow-up tickets instead:

1. `drf_actions/models.py:110-118` — `ActionContentType.create_events` iterates `DRF_ACTIONS_SETTINGS["content_types"].values()` but unpacks `key, content_type` (should be `.items()`); crashes if ever called.
2. `drf_actions/models.py:82-86` — `bulk_create_entities` dedups against `EventJournal.objects...values_list(pk, flat=True)` where `pk` is the *watched model's* pk name (`"id"`), so it compares journal row ids instead of `object_id`.

## Dependency target matrix (verified against PyPI, 2026-07)

| Package | Old pin | New pin | Notes |
|---|---|---|---|
| python | `^3.7` | `^3.10` | Django 5.2 requires ≥3.10 |
| Django | `>=3.2.14` | `>=4.2,<6.0` | 5.2.16 is current LTS patch; 4.2 kept installable for staged rollout |
| djangorestframework | `>=3.12.2` | `>=3.16` | 3.16 is the first with official Django 5.2 support (3.15 only covers 5.0); latest 3.17.1 |
| django-model-utils | `>=4.1.1` | `>=5.0.0` | 5.0.0 supports Django 5.x; `Choices` still present |
| django-filter | `>=22.1` | `>=24.3` | 24.3 supports Django ≤5.1; hosts on 5.2 resolve 25.x+ |
| djangorestframework-api-key | *(undeclared!)* | `>=3.1.0` | first release with Django 5 support |
| django-json-widget | *(undeclared!)* | `>=2.0.0` | 2.x supports Django 5 |
| pytest / pytest-django / psycopg[binary] | — | `>=8.0` / `>=4.8` / `>=3.2` | dev group only — the library itself must not depend on a DB driver |

## File structure

```
pyproject.toml                            # modify: deps, classifiers, version, pytest config, dev group
poetry.lock                               # regenerate
drf_actions/migrations/0001_initial.py    # modify: jsonb import removal
drf_actions/apps.py                       # modify: default_auto_field
tests/__init__.py                         # create (empty)
tests/settings.py                         # create: test Django settings (Postgres from env)
tests/urls.py                             # create: root urlconf including drf_actions.urls
tests/testapp/__init__.py                 # create (empty)
tests/testapp/apps.py                     # create: AppConfig (label "testapp")
tests/testapp/models.py                   # create: Author model (trigger target)
tests/testapp/migrations/__init__.py      # create (empty)
tests/testapp/migrations/0001_initial.py  # create: hand-written initial migration
tests/test_smoke.py                       # create: imports + ORM smoke (the "red" test for the jsonb bug)
tests/test_apps.py                        # create: default_auto_field check
tests/test_api.py                         # create: API-key auth, list, filter tests
tests/test_triggers.py                    # create: PG trigger integration tests
.github/workflows/tests.yml               # create: CI test matrix
.github/workflows/publish.yml             # modify: action version bumps
.pre-commit-config.yaml                   # modify: resolvable pins
README.md                                 # modify: requirements + dev section
```

`tests*` is already excluded from the built package (`exclude = ["tests*"]` in pyproject) — no packaging change needed for the new dir.

## Subagent model assignment (execution via superpowers:subagent-driven-development)

Orchestration and per-task review: **Fable** (main session). Task workers:

| Task | Worker model | Why |
|---|---|---|
| 1. Packaging & dependency bump | **sonnet** | Multi-file TOML surgery + lock regen; mechanical but must be exact |
| 2. Test harness | **opus** | Most design-heavy: settings, test app, docker DB; failure modes are subtle |
| 3. Fix migration 0001 | **haiku** | Two-line edit with the code given verbatim, verified by existing tests |
| 4. `default_auto_field` | **haiku** | One-line edit + given test |
| 5. API & filter tests | **sonnet** | Straightforward test authoring from provided code |
| 6. Trigger integration tests | **opus** | Raw plpgsql/transaction subtleties; highest risk of flaky misdiagnosis |
| 7. CI workflows | **sonnet** | YAML with a service container; moderate |
| 8. Tooling & docs housekeeping | **haiku** | Pin bumps and README text, all given verbatim |

---

### Task 1: Packaging & dependency bump

**Files:**
- Modify: `pyproject.toml`
- Regenerate: `poetry.lock`

- [ ] **Step 1: Update `pyproject.toml` metadata and dependencies**

Replace the `[tool.poetry]` header block (lines 1–23 region) so version, classifiers, and deps read exactly:

```toml
[tool.poetry]
name = "drf-actions"
version = "0.4.0"
description = "Create event log with help triggers and send notify after create event"
authors = ["Pavel Maltsev <pavel@speechki.org>"]
readme = "README.md"
homepage = "https://github.com/speechki-book/drf-actions"
license = "MIT"
keywords=["django", "restframework", "drf", "events", "log"]
classifiers = [
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Framework :: Django",
    "Framework :: Django :: 4.2",
    "Framework :: Django :: 5.2",
]
exclude = ["tests*"]

[tool.poetry.dependencies]
python = "^3.10"
Django = ">=4.2,<6.0"
djangorestframework = ">=3.16"
django-model-utils = ">=5.0.0"
django-filter = ">=24.3"
djangorestframework-api-key = ">=3.1.0"
django-json-widget = ">=2.0.0"

[tool.poetry.group.dev.dependencies]
pytest = ">=8.0"
pytest-django = ">=4.8"
psycopg = {version = ">=3.2", extras = ["binary"]}
```

Notes: this **replaces** the deprecated empty `[tool.poetry.dev-dependencies]` section (delete it). Everything below `[build-system]` (black/flake8/isort config) stays unchanged.

- [ ] **Step 2: Append pytest configuration** at the end of `pyproject.toml`:

```toml
[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "tests.settings"
testpaths = ["tests"]
```

- [ ] **Step 3: Regenerate the lock file**

```bash
cd /Users/kurbezz/work/speechki_dev_env/apps/drf-actions
uvx poetry lock
uvx poetry check
```

Expected: both commands exit 0. Poetry 2.x will print deprecation warnings about the legacy `[tool.poetry]`-only layout (no `[project]` table) — that is acceptable, do not restructure the file. (Poetry is not installed locally — always run it through `uvx poetry`.)

- [ ] **Step 4: Create the dev virtualenv and verify Django 5 resolves**

```bash
uv venv --python 3.13 .venv
uv pip install --python .venv/bin/python -e . pytest pytest-django "psycopg[binary]"
.venv/bin/python -c "import django, rest_framework, django_filters, model_utils, rest_framework_api_key, django_json_widget; print(django.get_version())"
```

Expected: prints a `5.2.x` version, no ImportError. (Local system Python is 3.14, which Django 5.2 does not support — hence `--python 3.13`; uv downloads it if missing.)

- [ ] **Step 5: Verify `.venv` is git-ignored, then commit**

```bash
grep -q '^\.venv' .gitignore || echo ".venv/" >> .gitignore
git add pyproject.toml poetry.lock .gitignore
git commit -m "SPB-1354: bump dependencies for Django 5.2 / Python 3.10+"
```

---

### Task 2: Test harness + smoke tests (green)

Note: the historical `jsonb` import in migration 0001 does NOT crash under Django 5 — Django ships a compat shim precisely so historical migrations keep loading. The suite is therefore expected to be green at the end of this task; Task 3's migration edit is verified by this suite staying green, not by a red→green transition.

**Files:**
- Create: `tests/__init__.py`, `tests/settings.py`, `tests/urls.py`
- Create: `tests/testapp/__init__.py`, `tests/testapp/apps.py`, `tests/testapp/models.py`
- Create: `tests/testapp/migrations/__init__.py`, `tests/testapp/migrations/0001_initial.py`
- Create: `tests/test_smoke.py`

- [ ] **Step 1: Start the test PostgreSQL** (port 54329 to avoid clashing with any local 5432):

```bash
docker run -d --name drf-actions-test-pg \
  -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=drf_actions \
  -p 54329:5432 postgres:16-alpine
docker exec drf-actions-test-pg sh -c 'until pg_isready -U postgres; do sleep 0.5; done'
```

Expected: `accepting connections`. (If the container already exists: `docker start drf-actions-test-pg`.)

- [ ] **Step 2: Create empty packages**

```bash
touch tests/__init__.py tests/testapp/__init__.py tests/testapp/migrations/__init__.py
```

(Create the directories first: `mkdir -p tests/testapp/migrations`.)

- [ ] **Step 3: Create `tests/settings.py`**

```python
import os


SECRET_KEY = "test-secret-key"
DEBUG = True
USE_TZ = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "drf_actions"),
        "USER": os.environ.get("POSTGRES_USER", "postgres"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "postgres"),
        "HOST": os.environ.get("POSTGRES_HOST", "127.0.0.1"),
        "PORT": os.environ.get("POSTGRES_PORT", "54329"),
    }
}

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "rest_framework",
    "rest_framework_api_key",
    "django_filters",
    "drf_actions",
    "tests.testapp",
]

ROOT_URLCONF = "tests.urls"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

DRF_ACTIONS_SETTINGS = {
    "content_types": {
        "author": {
            "pk": "id",
            "owner": None,
            "catch_update": [],
            "m2m": [],
            "model": ("testapp", "Author"),
            "fields": (("name", "name"),),
        }
    },
    "create_event_for_new_entity": True,
    "queue": "events",
    "route": "main",
}
```

Note: `drf_actions.app_settings` reads `settings.DRF_ACTIONS_SETTINGS` at import time, so the `content_type` choice value used throughout tests is `"author"`.

- [ ] **Step 4: Create `tests/urls.py`**

```python
from django.urls import include, path


urlpatterns = [path("", include("drf_actions.urls"))]
```

(This exposes the viewset at `/actions/events/` — `drf_actions/urls.py` adds the `actions/` prefix itself.)

- [ ] **Step 5: Create `tests/testapp/apps.py`**

```python
from django.apps import AppConfig


class TestAppConfig(AppConfig):
    name = "tests.testapp"
    label = "testapp"
    default_auto_field = "django.db.models.BigAutoField"
```

- [ ] **Step 6: Create `tests/testapp/models.py`**

```python
from django.db import models


class Author(models.Model):
    name = models.CharField(max_length=100)
```

- [ ] **Step 7: Create `tests/testapp/migrations/0001_initial.py`**

```python
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Author",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
            ],
        ),
    ]
```

- [ ] **Step 8: Create `tests/test_smoke.py`**

```python
import pytest

from drf_actions.models import EventJournal


def test_modules_import():
    import drf_actions.admin  # noqa: F401
    import drf_actions.signals  # noqa: F401
    import drf_actions.urls  # noqa: F401


@pytest.mark.django_db
def test_event_journal_create_and_str():
    obj = EventJournal.objects.create(
        reason="INSERT", content_type="author", object_id="1", data={"name": "A"}
    )
    assert str(obj) == "author : INSERT : 1"
```

- [ ] **Step 9: Run pytest and verify it passes**

```bash
.venv/bin/python -m pytest -x
```

Expected: PASS (both tests). Migrations 0001–0003 apply cleanly against Postgres — Django's `jsonb` compat shim keeps 0001 loadable, so this is a green run, not a red one. If it fails, it's most likely a Postgres connection/container issue — fix that before proceeding, not library code.

- [ ] **Step 10: Commit the harness**

```bash
git add tests/
git commit -m "SPB-1354: add pytest-django harness with Postgres-backed smoke tests"
```

---

### Task 3: Modernize migration 0001 (drop the jsonb compat shim)

**Files:**
- Modify: `drf_actions/migrations/0001_initial.py:3,107`

- [ ] **Step 1: Remove the dead import**

In `drf_actions/migrations/0001_initial.py`, delete line 3:

```python
import django.contrib.postgres.fields.jsonb
```

- [ ] **Step 2: Swap the field class**

In the same file (around line 107, `EventJournal`'s `data` field), replace:

```python
                (
                    "data",
                    django.contrib.postgres.fields.jsonb.JSONField(
                        blank=True, null=True
                    ),
                ),
```

with:

```python
                ("data", models.JSONField(blank=True, null=True)),
```

Rationale: `django.contrib.postgres.fields.JSONField` and `django.db.models.JSONField` both create a `jsonb` column on PostgreSQL — editing the historical migration is a no-op for already-migrated databases (migration 0003 already `AlterField`s to `models.JSONField`, so this only cleans up dead-API usage in a migration that would otherwise reference it forever) and removes reliance on a shim Django keeps only for backward compatibility.

- [ ] **Step 3: Run the full suite — still green**

```bash
.venv/bin/python -m pytest -v
```

Expected: `test_modules_import PASSED`, `test_event_journal_create_and_str PASSED` (migrations 0001–0003 apply against Postgres, including 0002's `rabbitmq` schema/plpgsql setup) — unchanged from Task 2's run, confirming the edit is behavior-neutral.

- [ ] **Step 4: Commit**

```bash
git add drf_actions/migrations/0001_initial.py
git commit -m "SPB-1354: drop deprecated jsonb compat import from initial migration"
```

---

### Task 4: `default_auto_field` on the AppConfig

**Files:**
- Modify: `drf_actions/apps.py`
- Create: `tests/test_apps.py`

- [ ] **Step 1: Write the failing test** — `tests/test_apps.py`:

```python
from drf_actions.apps import DRFActionsConfig


def test_default_auto_field_is_big_auto():
    assert DRFActionsConfig.default_auto_field == "django.db.models.BigAutoField"
```

- [ ] **Step 2: Run it, verify it fails**

```bash
.venv/bin/python -m pytest tests/test_apps.py -v
```

Expected: FAIL — `AttributeError` or assert on the inherited `"django.db.models.AutoField"`.

- [ ] **Step 3: Implement** — `drf_actions/apps.py` becomes:

```python
from django.apps import AppConfig


class DRFActionsConfig(AppConfig):
    name = "drf_actions"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        import drf_actions.signals
```

(Matches migration 0003, which already made both pks `BigAutoField` — so no schema drift, and host projects stop getting W042.)

- [ ] **Step 4: Full suite green**

```bash
.venv/bin/python -m pytest -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add drf_actions/apps.py tests/test_apps.py
git commit -m "SPB-1354: set default_auto_field=BigAutoField on app config"
```

---

### Task 5: API & filter tests

**Files:**
- Create: `tests/test_api.py`

- [ ] **Step 1: Write the tests** — `tests/test_api.py`:

```python
import pytest
from rest_framework.test import APIClient
from rest_framework_api_key.models import APIKey

from drf_actions.models import EventJournal


@pytest.fixture
def api_client():
    _, key = APIKey.objects.create_key(name="test")
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Api-Key {key}")
    return client


@pytest.mark.django_db
def test_events_endpoint_rejects_missing_api_key():
    assert APIClient().get("/actions/events/").status_code == 403


@pytest.mark.django_db
def test_events_endpoint_lists_events(api_client):
    EventJournal.objects.create(reason="INSERT", content_type="author", object_id="1", data={"name": "A"})
    response = api_client.get("/actions/events/")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["results"][0]["object_id"] == "1"
    assert set(body["results"][0].keys()) == {
        "id", "reason", "object_id", "content_type", "data", "created", "modified",
    }


@pytest.mark.django_db
def test_events_endpoint_filters_by_reason(api_client):
    EventJournal.objects.create(reason="INSERT", content_type="author", object_id="1", data={})
    EventJournal.objects.create(reason="DELETE", content_type="author", object_id="1", data={})
    response = api_client.get("/actions/events/", {"reason": "INSERT"})
    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["results"][0]["reason"] == "INSERT"
```

- [ ] **Step 2: Run them**

```bash
.venv/bin/python -m pytest tests/test_api.py -v
```

Expected: 3 PASSED. (These pass immediately — they pin current behavior under Django 5 rather than drive new code; that is the point of a migration test.)

- [ ] **Step 3: Commit**

```bash
git add tests/test_api.py
git commit -m "SPB-1354: add API endpoint tests (auth, list, filter)"
```

---

### Task 6: Postgres trigger integration tests

**Files:**
- Create: `tests/test_triggers.py`

Background for the executor: creating an `ActionContentType` fires a `post_save` signal (`drf_actions/signals.py`) that executes raw DDL — a plpgsql function + trigger on the watched table — and then backfills `EventJournal` for pre-existing rows. Row-level triggers run synchronously inside the test transaction, so plain `@pytest.mark.django_db` works; `transaction=True` is NOT needed.

- [ ] **Step 1: Write the tests** — `tests/test_triggers.py`:

```python
import pytest

from drf_actions.models import ActionContentType, EventJournal
from tests.testapp.models import Author


def make_content_type():
    return ActionContentType.objects.create(
        content_type="author", table=Author._meta.db_table
    )


@pytest.mark.django_db
def test_insert_update_delete_events_via_trigger():
    make_content_type()

    author = Author.objects.create(name="Alice")
    events = EventJournal.objects.filter(
        content_type="author", reason="INSERT", object_id=str(author.id)
    )
    assert events.count() == 1
    assert events.get().data == {"name": "Alice"}

    Author.objects.filter(pk=author.pk).update(name="Bob")
    update = EventJournal.objects.get(
        content_type="author", reason="UPDATE", object_id=str(author.id)
    )
    assert update.data == {"name": "Bob"}

    author.delete()
    delete = EventJournal.objects.get(
        content_type="author", reason="DELETE", object_id=str(author.id)
    )
    assert delete.data == {"name": "Bob"}


@pytest.mark.django_db
def test_existing_rows_backfilled_on_content_type_creation():
    author = Author.objects.create(name="Existing")

    make_content_type()

    backfill = EventJournal.objects.get(
        content_type="author", reason="INSERT", object_id=str(author.id)
    )
    # Backfill goes through the ORM path, which also includes the pk in data.
    assert backfill.data["name"] == "Existing"


@pytest.mark.django_db
def test_trigger_dropped_on_content_type_delete():
    act = make_content_type()
    act.delete()

    author = Author.objects.create(name="After")
    assert not EventJournal.objects.filter(
        content_type="author", object_id=str(author.id)
    ).exists()
```

- [ ] **Step 2: Run them**

```bash
.venv/bin/python -m pytest tests/test_triggers.py -v
```

Expected: 3 PASSED. If `test_insert_update_delete_events_via_trigger` fails on `data == {"name": "Alice"}`, inspect the actual `data` value before touching library code — the trigger builds JSON only from the configured `fields`, while the ORM backfill also injects the pk; do not "align" them.

- [ ] **Step 3: Full suite + commit**

```bash
.venv/bin/python -m pytest -v
git add tests/test_triggers.py
git commit -m "SPB-1354: add PostgreSQL trigger integration tests"
```

---

### Task 7: CI test workflow + publish workflow bump

**Files:**
- Create: `.github/workflows/tests.yml`
- Modify: `.github/workflows/publish.yml`

- [ ] **Step 1: Create `.github/workflows/tests.yml`**

```yaml
name: Tests

on:
  push:
    branches: [master]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        include:
          - django: "4.2"
            extra-pins: 'django-filter~=24.3'
          - django: "5.2"
            extra-pins: ''
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: drf_actions
        ports:
          - 54329:5432
        options: >-
          --health-cmd "pg_isready -U postgres"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 10
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install
        run: |
          pip install -e . "Django~=${{ matrix.django }}.0" ${{ matrix.extra-pins }} \
            pytest pytest-django "psycopg[binary]"

      - name: Test
        run: pytest -v
```

(The 4.2 leg pins `django-filter~=24.3` because newer django-filter releases dropped Django 4.2; pip's resolver would otherwise backtrack unpredictably.)

- [ ] **Step 2: Bump `publish.yml` action versions** — file becomes:

```yaml
name: Publish

on:
  create:
    tags:
      - '*'

jobs:
  Build-And-Publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 1

      - name: Build and publish to pypi
        uses: JRubics/poetry-publish@v2.1
        with:
          python_version: "3.12"
          pypi_token: ${{ secrets.PYPI_TOKEN }}
```

- [ ] **Step 3: Validate YAML locally**

```bash
.venv/bin/python -c "import yaml,glob; [yaml.safe_load(open(f)) for f in glob.glob('.github/workflows/*.yml')]" \
  || uvx --from pyyaml python -c "import yaml,glob; [yaml.safe_load(open(f)) for f in glob.glob('.github/workflows/*.yml')]"
```

Expected: exits 0. (PyYAML may not be in the venv; the `uvx` fallback covers that.)

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/tests.yml .github/workflows/publish.yml
git commit -m "SPB-1354: add CI test matrix (Django 4.2/5.2, Postgres); bump publish action"
```

---

### Task 8: Tooling & docs housekeeping

**Files:**
- Modify: `.pre-commit-config.yaml`
- Modify: `README.md`

- [ ] **Step 1: Fix pre-commit pins** — `.pre-commit-config.yaml` becomes:

```yaml
exclude: 'docs|node_modules|migrations|.git|.tox'

repos:
- repo: https://github.com/psf/black
  rev: 25.1.0
  hooks:
    - id: black
- repo: https://github.com/pycqa/isort
  rev: 6.0.1
  hooks:
    - id: isort
- repo: https://github.com/csachs/pyproject-flake8
  rev: v7.0.0
  hooks:
    - id: pyproject-flake8
```

(The old `rev: stable` for black no longer resolves; the pyflakes/pycodestyle git-pin workaround is obsolete.)

- [ ] **Step 2: Verify pre-commit runs**

```bash
uvx pre-commit run --all-files
```

Expected: hooks run; if black/isort reformat the new test files, re-run until clean and include the changes in the commit. If a hook `rev` fails to resolve, check the tag exists (`git ls-remote --tags <repo-url>`) and use the nearest available tag.

- [ ] **Step 3: Update `README.md`** — append:

```markdown
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
```

- [ ] **Step 4: Full suite one last time + commit**

```bash
.venv/bin/python -m pytest -v
git add .pre-commit-config.yaml README.md
git commit -m "SPB-1354: modernize pre-commit pins; document requirements and dev setup"
```

---

## Definition of done

- `pytest` green locally against Postgres 16 with Django 5.2.x on Python 3.13.
- CI `tests.yml` green on both matrix legs (4.2, 5.2).
- `poetry check` passes; `poetry.lock` regenerated.
- No behavior changes outside the two listed fixes (migration import, `default_auto_field`); out-of-scope bugs untouched.
- Version bumped to 0.4.0 (tag + publish happens after merge, via the existing tag-triggered workflow).
