from django.conf import settings
from model_utils import Choices


if hasattr(settings, "DRF_ACTIONS_SETTINGS"):
    DRF_ACTIONS_SETTINGS = settings.DRF_ACTIONS_SETTINGS
else:
    DRF_ACTIONS_SETTINGS = {
        "content_types": {
            "user": {
                "pk": "id",
                "owner": None,
                "catch_update": [],
                "m2m": [
                    (
                        "users_user_groups",
                        "group_id",
                        "user_id",
                        "auth_group",
                        "id",
                        "name",
                        "groups",
                    )
                ],
                "model": ("users", "user"),
                "fields": (
                    ("email", "email"),
                    ("photo", "photo"),
                    ("partner", "partner_id"),
                    ("full_name", "full_name",),
                ),
            }
        },
        "create_event_for_new_entity": True,
        "queue": "events",
        "route": "main",
    }


ACTION_EVENTS = DRF_ACTIONS_SETTINGS.get(
    "events", Choices("INSERT", "UPDATE", "DELETE",)
)

ACTION_CONTENT_TYPES = Choices(*DRF_ACTIONS_SETTINGS["content_types"].keys())

INIT_CONTENT_TYPE = DRF_ACTIONS_SETTINGS.get("create_event_for_new_entity", True)

ACTION_QUEUE = DRF_ACTIONS_SETTINGS.get("queue", "events")

ACTION_ROUTE = DRF_ACTIONS_SETTINGS.get("route", "main")
