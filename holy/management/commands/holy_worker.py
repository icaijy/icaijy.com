import time

from django.core.management.base import BaseCommand
from django.db import close_old_connections

from holy.collector import run_one


class Command(BaseCommand):
    help = 'Process Holy Competitive queue with independent API-rate upstream budgets.'

    def add_arguments(self, parser):
        parser.add_argument('--once', action='store_true', help='Try one job and exit (safe from a cron every minute).')

    def handle(self, *args, **options):
        try:
            while True:
                close_old_connections()
                message = run_one()
                if options['once'] or not message.startswith(('Waiting', 'Queue idle', 'Another')):
                    self.stdout.write(message)
                if options['once']:
                    return
                # Do not round 1.1/2.1-second gates up to the old 5-second poll.
                time.sleep(5 if message == 'Queue idle' else 1 if message.startswith('Another') else 0.2)
        except KeyboardInterrupt:
            self.stdout.write('Collector stopped; queued pages and request budget are preserved.')
