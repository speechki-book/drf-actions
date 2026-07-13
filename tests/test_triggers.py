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

    author_id = author.id
    author.delete()
    # Model.delete() clears instance.pk, so the id must be captured beforehand.
    delete = EventJournal.objects.get(
        content_type="author", reason="DELETE", object_id=str(author_id)
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
