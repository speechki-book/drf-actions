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
    "django.contrib.admin",
    "django.contrib.sessions",
    "django.contrib.messages",
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
