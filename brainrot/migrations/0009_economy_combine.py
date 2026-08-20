from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def seed_economy(apps, schema_editor):
    HOF = apps.get_model('brainrot', 'HallOfFameEntry')
    Balance = apps.get_model('brainrot', 'CurrencyBalance')
    Txn = apps.get_model('brainrot', 'CurrencyTransaction')
    Cosmetic = apps.get_model('brainrot', 'Cosmetic')
    Offer = apps.get_model('brainrot', 'CosmeticOffer')

    # Opening mark-to-market value for existing main-67 HOF assets.
    for entry in HOF.objects.filter(user__isnull=False, game_mode='six_seven').iterator():
        score = int(entry.score or 0)
        base = max(1, score * score // (67 * 67)) if score > 0 else 0
        value = base + max(1, base // 2) if base and entry.visibility == 'public' else base
        entry.asset_value_67 = value
        entry.asset_revision = 1 if value else 0
        entry.save(update_fields=['asset_value_67', 'asset_revision'])
        if not value:
            continue
        bal, _ = Balance.objects.get_or_create(user_id=entry.user_id, currency='67', defaults={'balance': 0, 'lifetime_earned': 0})
        bal.balance += value
        bal.lifetime_earned += value
        bal.save(update_fields=['balance', 'lifetime_earned'])
        Txn.objects.get_or_create(
            unique_key=f'hof-opening:{entry.pk}',
            defaults={
                'user_id': entry.user_id, 'currency': '67', 'amount': value,
                'reason': 'Opening HOF valuation', 'hall_entry_id': entry.pk,
                'metadata': {'score': score, 'visibility': entry.visibility, 'new_value': value},
            },
        )

    def add(name, slug, category, level, badge=''):
        palettes = [
            ('#65ff6a', '#102310'), ('#ffd95a', '#2b2106'), ('#6cecff', '#071f2b'),
            ('#ff5aa8', '#2b071a'), ('#ae6cff', '#170925'), ('#ff6b35', '#2b0c05'),
            ('#d8ff62', '#0b1020'),
        ]
        fg, bg = palettes[(level - 1) % len(palettes)]
        css = f'color:{fg}!important;background:{bg}!important;border-color:{fg}!important;'
        extra = ''
        if category == 'username':
            css = f'color:{fg}!important;font-weight:{700 + level * 40};text-shadow:0 0 {0.15 + level*.08:.2f}rem {fg};'
        elif category == 'hof':
            css += f'box-shadow:0 0 {0.4 + level*.25:.2f}rem {fg}55!important;background:linear-gradient(135deg,{bg},{fg}22,{bg})!important;'
        elif category == 'badge':
            css += 'font-weight:900;box-shadow:0 0 .65rem currentColor;'
        else:
            css += f'box-shadow:0 0 {0.3 + level*.2:.2f}rem {fg}55!important;'
        if level >= 4:
            css += 'background-size:300% 300%!important;animation:cosPulse 2.2s ease-in-out infinite alternate;'
            extra += '@keyframes cosPulse{to{filter:hue-rotate(55deg);transform:translateY(-1px)}}'
        if level >= 6:
            extra += '__SELECTOR__{position:relative;overflow:hidden}__SELECTOR__::after{content:"✦ 67 ✦";position:absolute;right:.35rem;top:.15rem;opacity:.22;font-weight:1000;animation:cosSpin 3s linear infinite}@keyframes cosSpin{to{transform:rotate(360deg)}}'
        item, _ = Cosmetic.objects.get_or_create(
            slug=slug,
            defaults={
                'name': name, 'category': category,
                'description': f'Preset tier {level}. More expensive, more CSS crimes.',
                'css': css, 'extra_css': extra, 'badge_text': badge, 'sort_order': level * 10,
            },
        )
        prices = (67 * level, 167 * level, 667 * level)
        for order, (price, days) in enumerate(zip(prices, (7, 30, None)), start=1):
            Offer.objects.get_or_create(
                cosmetic=item, currency='67', price=price, duration_days=days,
                defaults={'sort_order': order * 10},
            )

    username = [
        ('67 Green', '67-green'), ('Golden Swan', 'golden-swan'), ('Ice Protocol', 'ice-protocol'),
        ('RGB Brainrot', 'rgb-brainrot'), ('Void Glitch', 'void-glitch'), ('Hypernova 67', 'hypernova-67'),
        ('Reality Leak', 'reality-leak'),
    ]
    hof = [
        ('Lime Lab', 'hof-lime-lab'), ('Midnight Grid', 'hof-midnight-grid'), ('Golden Archive', 'hof-golden-archive'),
        ('Tung Tung Shrine', 'hof-tung-shrine'), ('Inferno Reactor', 'hof-inferno-reactor'),
        ('Event Horizon', 'hof-event-horizon'), ('THE 67', 'hof-the-67'),
    ]
    badges = [
        ('67 Badge', 'badge-67', '6️⃣7️⃣'), ('Skull Certified', 'badge-skull', '💀'), ('On Fire', 'badge-fire', '🔥'),
        ('GOAT', 'badge-goat', 'GOAT'), ('67 ELITE', 'badge-elite', '67 ELITE'), ('CENTRAL BANK', 'badge-central-bank', '🏦 67'),
    ]
    comments = [
        ('Terminal Review', 'comment-terminal'), ('Golden Opinion', 'comment-gold'), ('RGB Testimony', 'comment-rgb'),
        ('Void Reply', 'comment-void'), ('Glitch Witness', 'comment-glitch'), ('Nuclear Peer Review', 'comment-nuclear'),
    ]
    for level, (name, slug) in enumerate(username, 1):
        add(name, slug, 'username', level)
    for level, (name, slug) in enumerate(hof, 1):
        add(name, slug, 'hof', level)
    for level, (name, slug, badge) in enumerate(badges, 1):
        add(name, slug, 'badge', level, badge)
    for level, (name, slug) in enumerate(comments, 1):
        add(name, slug, 'comment', level)


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('brainrot', '0008_halloffamereaction'),
    ]

    operations = [
        migrations.AddField(model_name='halloffameentry', name='asset_revision', field=models.PositiveIntegerField(default=0)),
        migrations.AddField(model_name='halloffameentry', name='asset_value_67', field=models.PositiveIntegerField(default=0)),
        migrations.AddField(model_name='halloffameentry', name='metrics', field=models.JSONField(blank=True, default=dict)),
        migrations.AlterField(
            model_name='halloffameentry', name='game_mode',
            field=models.CharField(choices=[('six_seven', '67 Counter'), ('leg_claps', 'Tung Tung Leg Claps'), ('combine', '67 × Tung Tung Combine'), ('voice_67', 'Six Seven Voice Speedrun')], default='six_seven', max_length=16),
        ),
        migrations.AlterField(model_name='halloffameentry', name='score', field=models.PositiveIntegerField()),
        migrations.CreateModel(
            name='Cosmetic',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=80)), ('slug', models.SlugField(max_length=80, unique=True)),
                ('category', models.CharField(choices=[('username', 'Username'), ('hof', 'HOF background'), ('badge', 'Badge'), ('comment', 'Comment')], max_length=16)),
                ('description', models.CharField(blank=True, max_length=300)),
                ('css', models.TextField(blank=True, help_text='Raw CSS declarations applied to this cosmetic element.')),
                ('extra_css', models.TextField(blank=True, help_text='Optional full CSS. Use __SELECTOR__ for this cosmetic selector and __IMAGE_URL__ for image_url.')),
                ('badge_text', models.CharField(blank=True, max_length=40)), ('image_url', models.URLField(blank=True)),
                ('enabled', models.BooleanField(default=True)), ('sort_order', models.PositiveSmallIntegerField(default=100)),
            ], options={'ordering': ('category', 'sort_order', 'name')},
        ),
        migrations.CreateModel(
            name='DailySettlement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(unique=True)), ('settled_at', models.DateTimeField(auto_now_add=True)),
                ('participant_count', models.PositiveIntegerField(default=0)), ('distributed', models.PositiveIntegerField(default=0)),
            ], options={'ordering': ('-date',)},
        ),
        migrations.CreateModel(
            name='CurrencyBalance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('currency', models.CharField(choices=[('61', '61 Coin'), ('67', '67 Coin')], max_length=2)),
                ('balance', models.BigIntegerField(default=0)), ('lifetime_earned', models.BigIntegerField(default=0)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='brainrot_currency_balances', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='CurrencyTransaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('currency', models.CharField(choices=[('61', '61 Coin'), ('67', '67 Coin')], max_length=2)),
                ('amount', models.BigIntegerField()), ('reason', models.CharField(max_length=100)),
                ('unique_key', models.CharField(max_length=180, unique=True)), ('metadata', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('hall_entry', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='currency_transactions', to='brainrot.halloffameentry')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='brainrot_currency_transactions', to=settings.AUTH_USER_MODEL)),
            ], options={'ordering': ('-created_at', '-id')},
        ),
        migrations.CreateModel(
            name='CosmeticOffer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('currency', models.CharField(choices=[('61', '61 Coin'), ('67', '67 Coin')], default='67', max_length=2)),
                ('price', models.PositiveIntegerField()),
                ('duration_days', models.PositiveIntegerField(blank=True, help_text='Blank means permanent.', null=True)),
                ('enabled', models.BooleanField(default=True)), ('sort_order', models.PositiveSmallIntegerField(default=100)),
                ('cosmetic', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='offers', to='brainrot.cosmetic')),
            ], options={'ordering': ('sort_order', 'price', 'id')},
        ),
        migrations.CreateModel(
            name='UserCosmetic',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('expires_at', models.DateTimeField(blank=True, null=True)), ('acquired_at', models.DateTimeField(auto_now_add=True)),
                ('cosmetic', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='owners', to='brainrot.cosmetic')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='brainrot_cosmetics', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='EquippedCosmetic',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category', models.CharField(choices=[('username', 'Username'), ('hof', 'HOF background'), ('badge', 'Badge'), ('comment', 'Comment')], max_length=16)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('cosmetic', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='equipped_by', to='brainrot.cosmetic')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='brainrot_equipped_cosmetics', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddConstraint(model_name='currencybalance', constraint=models.UniqueConstraint(fields=('user', 'currency'), name='currency_balance_user_uniq')),
        migrations.AddIndex(model_name='currencybalance', index=models.Index(fields=['currency', '-balance'], name='currency_wealth_rank_idx')),
        migrations.AddIndex(model_name='currencytransaction', index=models.Index(fields=['user', 'currency', '-created_at'], name='coin_user_currency_idx')),
        migrations.AddConstraint(model_name='usercosmetic', constraint=models.UniqueConstraint(fields=('user', 'cosmetic'), name='user_cosmetic_uniq')),
        migrations.AddConstraint(model_name='equippedcosmetic', constraint=models.UniqueConstraint(fields=('user', 'category'), name='equipped_cosmetic_category_uniq')),
        migrations.RunPython(seed_economy, migrations.RunPython.noop),
    ]
