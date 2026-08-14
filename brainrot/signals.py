from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import HallOfFameEntry


@receiver(post_delete, sender=HallOfFameEntry)
def delete_recording_with_entry(sender, instance, **kwargs):
    if instance.video:
        instance.video.delete(save=False)
