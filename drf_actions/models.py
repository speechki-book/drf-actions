from django.db import models
from django.db.models.fields import files
from django.apps import apps
from model_utils.models import TimeStampedModel
from typing import Type, Tuple, List, Dict
from drf_actions.app_settings import (
    DRF_ACTIONS_SETTINGS,
    ACTION_EVENTS,
    ACTION_CONTENT_TYPES,
    INIT_CONTENT_TYPE,
)
from itertools import islice
from django.db import connection


class EventJournal(TimeStampedModel):
    REASONS = ACTION_EVENTS
    CONTENT_TYPES = ACTION_CONTENT_TYPES

    reason = models.CharField(max_length=30, choices=REASONS, db_index=True)
    object_id = models.CharField(max_length=100, db_index=True)
    content_type = models.CharField(max_length=50, choices=CONTENT_TYPES, db_index=True)
    data = models.JSONField(blank=True, null=True)

    def __str__(self):
        return f"{self.content_type} : {self.reason} : {self.object_id}"


class ActionContentType(TimeStampedModel):
    CONTENT_TYPES = ACTION_CONTENT_TYPES

    content_type = models.CharField(max_length=50, choices=CONTENT_TYPES, db_index=True)
    table = models.CharField(max_length=100)

    @staticmethod
    def prepare_event_journal(
        objs,
        content_type: str,
        pk: str,
        fields_dict: Dict[str, str],
        m2m: List[Tuple[str, str]],
    ):
        owner = DRF_ACTIONS_SETTINGS["content_types"][content_type].get("owner")
        for obj in objs:
            data = {}
            for key, value in fields_dict.items():
                attr_value = getattr(obj, key)
                if isinstance(attr_value, files.FieldFile) and attr_value.name:
                    data[value] = attr_value.url
                elif isinstance(attr_value, files.FieldFile) and not attr_value.name:
                    data[value] = None
                else:
                    data[value] = attr_value

            for m2m_field, attr_name in m2m:
                data[m2m_field] = [
                    getattr(item, attr_name) for item in getattr(obj, m2m_field).all()
                ]

            if owner:
                data["owner"] = getattr(obj, owner)

            yield EventJournal(
                reason=ACTION_EVENTS.INSERT,
                content_type=content_type,
                object_id=getattr(obj, pk),
                data=data,
            )

    def bulk_create_entities(self, model: Type["models.Model"], content_type: str):
        m2m = [
            (item[6], item[5])
            for item in DRF_ACTIONS_SETTINGS["content_types"][content_type]["m2m"]
        ]
        prefetch = [item[0] for item in m2m]
        pk = DRF_ACTIONS_SETTINGS["content_types"][content_type]["pk"]
        fields_dict = {
            item[1]: item[0]
            for item in DRF_ACTIONS_SETTINGS["content_types"][content_type]["fields"]
        }
        fields_dict[pk] = pk
        current_objects = set(
            EventJournal.objects.filter(content_type=content_type).values_list(
                pk, flat=True
            )
        )
        queryset = set(model.objects.all().values_list(pk, flat=True))
        obj_ids = queryset.difference(current_objects)
        objs = model.objects.prefetch_related(*prefetch).filter(pk__in=obj_ids)

        new_objs = self.prepare_event_journal(objs, content_type, pk, fields_dict, m2m)

        while True:
            batch = list(islice(new_objs, 100))
            if not batch:
                break

            EventJournal.objects.bulk_create(batch, 100)

    def create_current_type_events(self):
        app_name, model_name = DRF_ACTIONS_SETTINGS["content_types"][self.content_type][
            "model"
        ]
        model: Type["models.Model"] = apps.get_model(
            app_label=app_name, model_name=model_name
        )
        self.bulk_create_entities(model, self.content_type)

    @classmethod
    def create_events(cls):
        content_types = cls.objects.values_list("content_type", flat=True)
        for key, content_type in DRF_ACTIONS_SETTINGS["content_types"].values():
            if key not in content_types:
                app_name, model_name = content_type["model"]
                model: Type["models.Model"] = apps.get_model(
                    app_label=app_name, model_name=model_name
                )
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

    def m2m_init(self):
        m2m = DRF_ACTIONS_SETTINGS["content_types"][self.content_type].get("m2m")

        if not m2m:
            return "", "", []

        m2m_init_variables = []
        m2m_calc_variables = []
        m2m_values = []
        for item in m2m:
            m2m_init_variables.append(f"{item[6]} json;")
            m2m_calc_variables.append(
                f"{item[6]}:= json_agg(tmp.{item[5]})::jsonb from (select name from {item[0]} left join {item[3]} ag on"
                f" {item[0]}.{item[1]} = ag.{item[4]} where {item[0]}.{item[2]} = NEW.id) as tmp;"
            )
            m2m_values.append(f"'{item[6]}',{item[6]}")

        return "\n".join(m2m_init_variables), "\n".join(m2m_calc_variables), m2m_values

    def owner(self):
        owner = DRF_ACTIONS_SETTINGS["content_types"][self.content_type].get("owner")

        if not owner:
            return []

        return ["'owner'", f"NEW.{owner}"]

    def create_trigger_function(self):
        prefix = self.trigger_prefix()
        build_json = []
        delete_build_json = []
        for field in DRF_ACTIONS_SETTINGS["content_types"][self.content_type]["fields"]:
            build_json.append(f"'{field[0]}'")
            build_json.append(f"NEW.{field[1]}")

            delete_build_json.append(f"'{field[0]}'")
            delete_build_json.append(f"OLD.{field[1]}")

        m2to_variables, m2m_calc, m2m_values = self.m2m_init()
        owner = self.owner()

        build_json_str = ",".join(build_json + m2m_values + owner)
        delete_build_json_str = ",".join(delete_build_json + owner)
        pk = DRF_ACTIONS_SETTINGS["content_types"][self.content_type]["pk"]

        func = f"""CREATE OR REPLACE FUNCTION public.{prefix}{self.content_type}_func() RETURNS TRIGGER AS
                $BODY$
                declare
                    json_new jsonb;
                    reason varchar;
                    {m2to_variables}
                BEGIN
                    IF tg_op = 'DELETE' THEN
                        json_new:= json_build_object({delete_build_json_str});
                        INSERT INTO {EventJournal._meta.db_table}(reason, object_id, content_type, data, created, modified)
                            VALUES (tg_op ,OLD.{pk}, '{self.content_type}', json_new, now(), now());
                    ELSE
                        {m2m_calc}
                        json_new:= json_build_object({build_json_str});
                        INSERT INTO {EventJournal._meta.db_table}(reason, object_id, content_type, data, created, modified)
                            VALUES (tg_op ,NEW.{pk}, '{self.content_type}', json_new, now(), now());
                    END IF;
                        RETURN null; 
                END; $BODY$ LANGUAGE plpgsql;"""

        with connection.cursor() as cursor:
            cursor.execute(func)

    def init_triggers(self):
        prefix = self.trigger_prefix()

        catch_update = DRF_ACTIONS_SETTINGS["content_types"][self.content_type].get(
            "catch_update"
        )

        if catch_update:
            catch_fields = " of " + ",".join(catch_update)
        else:
            catch_fields = ""

        trigger = f"""create trigger {prefix}{self.content_type}_trigger
                                after insert or update {catch_fields} or delete on {self.table}
                                for each row execute procedure public.{prefix}{self.content_type}_func();
                            """

        self.create_trigger_function()
        with connection.cursor() as cursor:
            cursor.execute(trigger)
