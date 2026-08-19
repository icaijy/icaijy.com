import os
import uuid

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from brainrot.models import HallOfFameEntry
from brainrot.video_mp4 import Mp4TranscodeError, transcode_path_to_mp4


class Command(BaseCommand):
    help = 'Convert existing Hall of Fame recordings to canonical H.264/AAC MP4 files.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--keep-going',
            action='store_true',
            help='Continue converting other entries after one conversion fails.',
        )

    def handle(self, *args, **options):
        keep_going = options['keep_going']
        entries = HallOfFameEntry.objects.order_by('pk')
        converted = 0
        skipped = 0
        failures = []

        for entry in entries.iterator():
            name = entry.video.name or ''
            if entry.mime_type == 'video/mp4' and name.lower().endswith('.mp4'):
                skipped += 1
                continue

            old_name = name
            storage = entry.video.storage
            try:
                source_path = entry.video.path
            except (AttributeError, NotImplementedError) as exc:
                message = f'HOF #{entry.pk}: storage has no local path ({exc})'
                failures.append(message)
                self.stderr.write(self.style.ERROR(message))
                if not keep_going:
                    raise CommandError(message) from exc
                continue

            new_name = f'hall_of_fame/{uuid.uuid4().hex}.mp4'
            try:
                with transcode_path_to_mp4(source_path) as output_path:
                    with open(output_path, 'rb') as handle:
                        saved_name = storage.save(new_name, File(handle, name=os.path.basename(new_name)))

                try:
                    with transaction.atomic():
                        entry.video.name = saved_name
                        entry.mime_type = 'video/mp4'
                        entry.save(update_fields=['video', 'mime_type'])
                except Exception:
                    storage.delete(saved_name)
                    raise

                if old_name and old_name != saved_name:
                    storage.delete(old_name)
                converted += 1
                self.stdout.write(self.style.SUCCESS(f'HOF #{entry.pk}: {old_name} -> {saved_name}'))
            except (Mp4TranscodeError, OSError, Exception) as exc:
                message = f'HOF #{entry.pk}: {exc}'
                failures.append(message)
                self.stderr.write(self.style.ERROR(message))
                if not keep_going:
                    raise CommandError(message) from exc

        self.stdout.write(
            self.style.SUCCESS(
                f'Done: {converted} converted, {skipped} already MP4, {len(failures)} failed.'
            )
        )
        if failures:
            raise CommandError('Some HOF videos could not be converted; originals were left intact.')
