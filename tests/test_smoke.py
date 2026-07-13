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
