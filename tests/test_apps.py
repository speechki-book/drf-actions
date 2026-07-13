from drf_actions.apps import DRFActionsConfig


def test_default_auto_field_is_big_auto():
    assert DRFActionsConfig.default_auto_field == "django.db.models.BigAutoField"
