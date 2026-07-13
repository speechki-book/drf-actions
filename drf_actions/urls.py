from django.urls import include, path

from rest_framework.routers import DefaultRouter

from drf_actions.views import EventJournalViewSet


router = DefaultRouter()
router.register(r"events", EventJournalViewSet, basename="event")


urlpatterns = [path("actions/", include(router.urls))]
