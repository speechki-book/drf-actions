from rest_framework import serializers
from drf_actions.models import EventJournal


class EventJournalSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventJournal
        fields = (
            "id",
            "reason",
            "object_id",
            "content_type",
            "data",
            "created",
            "modified",
        )
