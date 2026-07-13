from django.apps import AppConfig


class DRFActionsConfig(AppConfig):
    name = "drf_actions"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        import drf_actions.signals
