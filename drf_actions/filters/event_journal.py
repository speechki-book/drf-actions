from django_filters import FilterSet

from drf_actions.models import EventJournal


class EventJournalFilterSet(FilterSet):

    class Meta:
        model = EventJournal
        fields = {
        "id": ["exact", "in", "lt", "lte", "gt", "gte"],
        "created": ["range", "lt", "gt", "lte", "gte"],
        "reason": ["exact", "in"],
        "content_type": ["exact", "in"],
    }
