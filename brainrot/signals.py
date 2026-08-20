from django.db.models.signals import post_delete, post_save, pre_delete
from django.dispatch import receiver

from .models import HallOfFameEntry


@receiver(post_save, sender=HallOfFameEntry)
def revalue_hof_asset(sender, instance, **kwargs):
    # Lazy import avoids a circular import while Django is loading models.
    from .economy import sync_hof_asset_value
    sync_hof_asset_value(instance)


@receiver(pre_delete, sender=HallOfFameEntry)
def remove_hof_backing(sender, instance, **kwargs):
    from .economy import remove_hof_asset
    remove_hof_asset(instance)


@receiver(post_delete, sender=HallOfFameEntry)
def delete_recording_with_entry(sender, instance, **kwargs):
    if instance.video:
        instance.video.delete(save=False)
