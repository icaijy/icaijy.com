import os

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible


@deconstructible
class PrivateMediaStorage(FileSystemStorage):
    """Storage without a public URL; files are streamed by a guarded view."""

    def __init__(self):
        super().__init__(base_url=None)

    @property
    def base_location(self):
        return settings.PRIVATE_MEDIA_ROOT

    @property
    def location(self):
        return os.path.abspath(self.base_location)


private_media_storage = PrivateMediaStorage()
