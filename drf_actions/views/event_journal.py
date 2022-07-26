from rest_framework import viewsets, pagination, filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework_api_key.permissions import HasAPIKey
from drf_actions.filters.event_journal import EventJournalFilterSet
from drf_actions.serializers.event_journal import EventJournalSerializer
from drf_actions.models import EventJournal


class StandardPagination(pagination.PageNumberPagination):
    page_size = 100
    page_size_query_param = "page_size"
    max_page_size = 10000


class EventJournalViewSet(viewsets.ReadOnlyModelViewSet):
    filter_backends = [
        filters.SearchFilter,
        DjangoFilterBackend,
        filters.OrderingFilter,
    ]
    serializer_class = EventJournalSerializer
    queryset = EventJournal.objects.all().order_by("-created")
    permission_classes = (HasAPIKey,)
    pagination_class = StandardPagination
    filterset_class = EventJournalFilterSet
    ordering_fields = (
        "id",
        "created",
    )
