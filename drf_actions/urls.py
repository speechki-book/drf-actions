from drf_actions.views import EventJournalViewSet
from rest_framework.routers import DefaultRouter
from django.urls import include, path


router = DefaultRouter()
router.register(r"events", EventJournalViewSet, basename="event")


urlpatterns = [path("actions/", include(router.urls))]
