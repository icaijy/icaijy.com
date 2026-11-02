from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from holy.models import Account, CollectorState, Job


class Command(BaseCommand):
    help = 'Report collector heartbeat, coverage and queue without upstream requests.'

    def add_arguments(self, parser):
        parser.add_argument('--check', action='store_true', help='Exit nonzero if there is no recent worker heartbeat.')

    def handle(self, *args, **options):
        now = timezone.now()
        state = CollectorState.objects.filter(pk=1).first()
        for platform in ('cf', 'ac'):
            peers = Account.objects.filter(platform=platform, is_peer=True)
            self.stdout.write(f'{platform}: {peers.filter(synced_at__isnull=False).count()}/{peers.count()} peers synced; '
                              f'{peers.filter(synced_at__gte=now - timedelta(hours=36)).count()} fresh within 36h')
        self.stdout.write(f'Pending requests ready now: {Job.objects.filter(ready_at__lte=now).count()}')
        self.stdout.write(f'Worker heartbeat: {state.last_heartbeat if state else None}')
        self.stdout.write(f'Last completed request: {state.last_finished if state else None}')
        self.stdout.write(f'Last successful request: {state.last_success if state else None}')
        self.stdout.write(f'Next request allowed: {state.next_request_at if state else None}')
        for job in Job.objects.exclude(error='').order_by('ready_at')[:10]:
            self.stdout.write(f'{job.key}: {job.error}; next try {job.ready_at}')
        if options['check'] and (not state or not state.last_heartbeat or state.last_heartbeat < now - timedelta(minutes=15)):
            raise CommandError('No collector heartbeat within 15 minutes. Start/check holy_worker; full roster coverage is separate.')
