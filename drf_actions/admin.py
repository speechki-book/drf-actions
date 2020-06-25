from django.contrib import admin
from django.contrib.postgres import fields
from django_json_widget.widgets import JSONEditorWidget
from drf_actions.models import ActionContentType, EventJournal


@admin.register(ActionContentType)
class ActionContentTypeAdmin(admin.ModelAdmin):
    list_display = ["id", "content_type", "table"]


@admin.register(EventJournal)
class EventJournalAdmin(admin.ModelAdmin):
    list_display = ["id", "reason", "object_id", "content_type"]

    formfield_overrides = {
        fields.JSONField: {'widget': JSONEditorWidget},
    }
