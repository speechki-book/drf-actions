from rest_framework import viewsets, pagination, filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework_api_key.permissions import HasAPIKey
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
    filter_fields = {
        "id": ["exact", "in", "lt", "lte", "gt", "gte"],
        "created": ["range", "lt", "gt", "lte", "gte"],
        "reason": ["exact", "in"],
        "content_type": ["exact", "in"],
    }
    ordering_fields = (
        "id",
        "created",
    )
