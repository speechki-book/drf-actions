from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from drf_actions.models import ActionContentType
from drf_actions.app_settings import INIT_CONTENT_TYPE


@receiver(post_delete, sender=ActionContentType)
def drop_trigger_signal(sender, instance, using, **kwargs):
    instance.drop_trigger()


@receiver(post_save, sender=ActionContentType)
def create_trigger_signal(sender, instance, created, **kwargs):
    if created:
        instance.init_triggers()

        if INIT_CONTENT_TYPE:
            instance.create_current_type_events()
