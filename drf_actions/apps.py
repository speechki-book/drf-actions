from django.apps import AppConfig


class DRFActionsConfig(AppConfig):
    name = "drf_actions"

    def ready(self):
        import drf_actions.signals
