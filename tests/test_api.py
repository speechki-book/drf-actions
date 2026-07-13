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
