from django.db import models
from django.contrib.postgres.fields import JSONField
from django.apps import apps
from model_utils.models import TimeStampedModel
from typing import Type
from drf_actions.app_settings import DRF_ACTIONS_SETTINGS, ACTION_EVENTS, ACTION_CONTENT_TYPES, INIT_CONTENT_TYPE
from itertools import islice
from django.db import connection


class EventJournal(TimeStampedModel):
    REASONS = ACTION_EVENTS
    CONTENT_TYPES = ACTION_CONTENT_TYPES

    reason = models.CharField(max_length=30, choices=REASONS, db_index=True)
    object_id = models.CharField(max_length=100, db_index=True)
    content_type = models.CharField(max_length=50, choices=CONTENT_TYPES, db_index=True)
    data = JSONField(blank=True, null=True)

    def __str__(self):
        return f"{self.content_type} : {self.reason} : {self.object_id}"


class ActionContentType(TimeStampedModel):
    CONTENT_TYPES = ACTION_CONTENT_TYPES

    content_type = models.CharField(max_length=50, choices=CONTENT_TYPES, db_index=True)
    table = models.CharField(max_length=100)

    @staticmethod
    def bulk_create_entities(model: Type["models.Model"], content_type: str):
        current_objects = set(EventJournal.objects.filter(content_type=content_type).values_list("pk", flat=True))
        queryset = set(model.objects.all().values_list("pk", flat=True))
        obj_ids = queryset.difference(current_objects)
        objs = model.objects.filter(pk__in=obj_ids)\
            .values("pk", *DRF_ACTIONS_SETTINGS["content_types"][content_type]["fields"])

        new_objs = (
            EventJournal(
                reason=ACTION_EVENTS.INSERT,
                object_id=obj["pk"],
                content_type=content_type,
                data=obj
            ) for obj in objs
        )

        while True:
            batch = list(islice(new_objs, 100))
            if not batch:
                break

            EventJournal.objects.bulk_create(batch, 100)

    def create_current_type_events(self):
        app_name, model_name = DRF_ACTIONS_SETTINGS["content_types"][self.content_type]["model"]
        model: Type["models.Model"] = apps.get_model(app_label=app_name, model_name=model_name)
        self.bulk_create_entities(model, self.content_type)

    @classmethod
    def create_events(cls):
        content_types = cls.objects.values_list("content_type", flat=True)
        for key, content_type in DRF_ACTIONS_SETTINGS["content_types"].values():
            if key not in content_types:
                app_name, model_name = content_type["model"]
                model: Type["models.Model"] = apps.get_model(app_label=app_name, model_name=model_name)
                cls.objects.create(content_type=key, table=model._meta.db_table)

    @classmethod
    def delete_content_types(cls, content_types):
        for_delete_content_types = cls.objects.exclude(content_type__in=content_types)
        for content_type in for_delete_content_types:
            content_type.delete()

    @classmethod
    def init_content_type(cls):
        if INIT_CONTENT_TYPE:
            cls.create_events()

    @staticmethod
    def trigger_prefix():
        return "action_"

    def drop_trigger(self):
        prefix = self.trigger_prefix()
        query = f"DROP TRIGGER IF EXISTS {prefix}{self.content_type}_trigger ON {self.table};"
        func = f"DROP FUNCTION IF EXISTS public.{prefix}{self.content_type}_func"

        with connection.cursor() as cursor:
            cursor.execute(query)
            cursor.execute(func)

    def create_trigger_function(self):
        prefix = self.trigger_prefix()
        build_json = []
        for field in DRF_ACTIONS_SETTINGS["content_types"][self.content_type]["fields"]:
            build_json.append(f"'{field}'")
            build_json.append(f"NEW.{field}")

        build_json_str = ",".join(build_json)
        pk = DRF_ACTIONS_SETTINGS["content_types"][self.content_type]["pk"]

        func = f"""CREATE OR REPLACE FUNCTION public.{prefix}{self.content_type}_func() RETURNS TRIGGER AS
                $BODY$
                declare
                    json_new jsonb;
                    reason varchar;
                BEGIN
                    json_new:= json_build_object({build_json_str});
                    INSERT INTO {EventJournal._meta.db_table}(reason, object_id, content_type, data, created, modified)
                        VALUES (tg_op ,NEW.{pk}, '{self.content_type}', json_new, now(), now());
                        RETURN null; 
                END; $BODY$ LANGUAGE plpgsql;"""

        with connection.cursor() as cursor:
            cursor.execute(func)

    def init_triggers(self):
        prefix = self.trigger_prefix()
        trigger = f"""create trigger {prefix}{self.content_type}_trigger
                                after insert or update or delete on {self.table}
                                for each row execute procedure public.{prefix}{self.content_type}_func();
                            """

        self.create_trigger_function()
        with connection.cursor() as cursor:
            cursor.execute(trigger)