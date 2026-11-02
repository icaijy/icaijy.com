from django.db import models


class Account(models.Model):
    platform = models.CharField(max_length=2, choices=[('cf', 'Codeforces'), ('ac', 'AtCoder')])
    handle = models.CharField(max_length=40)
    handle_key = models.CharField(max_length=40)
    rating = models.IntegerField(null=True)
    is_peer = models.BooleanField(default=False, db_index=True)
    roster_seen = models.DateTimeField(null=True)
    verified = models.BooleanField(default=False)
    # Query accounts receive a lifetime backfill; peers need only recent activity.
    comparison_requested = models.DateTimeField(null=True)
    history_complete = models.BooleanField(default=False)
    synced_at = models.DateTimeField(null=True)
    latest_second = models.BigIntegerField(default=0)
    error = models.CharField(max_length=240, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['platform', 'handle_key'], name='holy_unique_account')]

    @property
    def url(self):
        return ('https://codeforces.com/profile/' if self.platform == 'cf' else 'https://atcoder.jp/users/') + self.handle


class Problem(models.Model):
    platform = models.CharField(max_length=2)
    key = models.CharField(max_length=100)
    contest = models.CharField(max_length=100)
    title = models.CharField(max_length=300)
    difficulty = models.IntegerField(null=True)
    tags = models.JSONField(default=list)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['platform', 'key'], name='holy_unique_problem')]

    @property
    def url(self):
        if self.platform == 'cf':
            contest, index = self.key.split('/', 1)
            if int(contest) >= 100000:
                return f'https://codeforces.com/gym/{contest}/problem/{index}'
            return f'https://codeforces.com/problemset/problem/{contest}/{index}'
        return f'https://atcoder.jp/contests/{self.contest}/tasks/{self.key}'


class Activity(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE)
    last_attempt = models.DateTimeField(db_index=True)
    last_ac = models.DateTimeField(null=True, db_index=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['account', 'problem'], name='holy_unique_activity')]


class Job(models.Model):
    key = models.CharField(max_length=100, unique=True)
    kind = models.CharField(max_length=30)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, null=True)
    payload = models.JSONField(default=dict)
    ready_at = models.DateTimeField(db_index=True)
    priority = models.IntegerField(default=0)
    failures = models.IntegerField(default=0)
    error = models.CharField(max_length=240, blank=True)
    updated_at = models.DateTimeField(auto_now=True)


class CollectorState(models.Model):
    # Singleton + compare-and-swap lease: covers multiple workers/processes.
    id = models.PositiveSmallIntegerField(primary_key=True, default=1)
    next_request_at = models.DateTimeField()  # Legacy diagnostic; per-origin gates live below.
    upstream_state = models.JSONField(default=dict)
    lease_until = models.DateTimeField()
    last_heartbeat = models.DateTimeField(null=True)
    last_started = models.DateTimeField(null=True)
    last_finished = models.DateTimeField(null=True)
    last_success = models.DateTimeField(null=True)
    maintenance_at = models.DateTimeField(null=True)
    error = models.CharField(max_length=240, blank=True)


class QueryBudget(models.Model):
    key = models.CharField(max_length=64, primary_key=True)
    count = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField()
