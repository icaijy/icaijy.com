import time

from django.core.management.base import BaseCommand
from django.db import close_old_connections

from holy.collector import run_one


class Command(BaseCommand):
    help = 'Process Holy Competitive queue with a shared 180-second upstream budget.'

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
                time.sleep(5)
        except KeyboardInterrupt:
            self.stdout.write('Collector stopped; queued pages and request budget are preserved.')
