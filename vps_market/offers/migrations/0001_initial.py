from __future__ import annotations

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Provider",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(max_length=80, unique=True)),
                ("name", models.CharField(max_length=160)),
                ("base_url", models.URLField(blank=True, max_length=500)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "providers", "ordering": ["slug"]},
        ),
        migrations.CreateModel(
            name="CrawlRun",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("provider_slug", models.SlugField(db_index=True, max_length=80)),
                ("status", models.CharField(default="running", max_length=40)),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("fetched_count", models.IntegerField(default=0)),
                ("upserted_count", models.IntegerField(default=0)),
                ("error", models.TextField(blank=True, null=True)),
            ],
            options={"db_table": "crawl_runs", "ordering": ["-started_at"]},
        ),
        migrations.CreateModel(
            name="ServerOffer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_offer_id", models.CharField(max_length=220)),
                ("name", models.CharField(max_length=240)),
                ("region", models.CharField(blank=True, max_length=120, null=True)),
                ("country", models.CharField(blank=True, max_length=120, null=True)),
                ("city", models.CharField(blank=True, max_length=120, null=True)),
                ("category", models.CharField(blank=True, max_length=160, null=True)),
                ("billing_period", models.CharField(default="monthly", max_length=40)),
                ("price_amount_irr", models.BigIntegerField(blank=True, null=True)),
                ("original_price_amount", models.BigIntegerField(blank=True, null=True)),
                ("original_price_currency", models.CharField(blank=True, max_length=40, null=True)),
                ("cpu_cores", models.FloatField(blank=True, null=True)),
                ("ram_mb", models.IntegerField(blank=True, null=True)),
                ("disk_gb", models.FloatField(blank=True, null=True)),
                ("disk_type", models.CharField(blank=True, max_length=80, null=True)),
                ("traffic_gb", models.FloatField(blank=True, null=True)),
                ("bandwidth_mbps", models.FloatField(blank=True, null=True)),
                ("has_gpu", models.BooleanField(default=False)),
                ("gpu_model", models.CharField(blank=True, max_length=160, null=True)),
                ("gpu_memory_mb", models.IntegerField(blank=True, null=True)),
                ("available", models.BooleanField(default=True)),
                ("buy_url", models.URLField(blank=True, max_length=1000, null=True)),
                ("source_url", models.URLField(blank=True, max_length=1000, null=True)),
                ("raw_payload", models.JSONField(default=dict)),
                ("first_seen_at", models.DateTimeField(auto_now_add=True)),
                ("last_seen_at", models.DateTimeField()),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "provider",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="offers",
                        to="offers.provider",
                    ),
                ),
            ],
            options={
                "db_table": "server_offers",
                "ordering": ["price_amount_irr", "provider__slug", "name"],
            },
        ),
        migrations.AddIndex(
            model_name="serveroffer",
            index=models.Index(fields=["provider", "region"], name="offer_provider_region_idx"),
        ),
        migrations.AddIndex(
            model_name="serveroffer",
            index=models.Index(fields=["price_amount_irr"], name="offer_price_idx"),
        ),
        migrations.AddIndex(
            model_name="serveroffer",
            index=models.Index(fields=["has_gpu"], name="offer_gpu_idx"),
        ),
        migrations.AddIndex(
            model_name="serveroffer",
            index=models.Index(fields=["available"], name="offer_available_idx"),
        ),
        migrations.AddIndex(
            model_name="serveroffer",
            index=models.Index(fields=["cpu_cores"], name="offer_cpu_idx"),
        ),
        migrations.AddIndex(
            model_name="serveroffer",
            index=models.Index(fields=["ram_mb"], name="offer_ram_idx"),
        ),
        migrations.AddConstraint(
            model_name="serveroffer",
            constraint=models.UniqueConstraint(
                fields=("provider", "source_offer_id", "region", "billing_period"),
                name="uq_offer_source_region_period",
            ),
        ),
    ]
