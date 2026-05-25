from __future__ import annotations

from django.db import models


class Provider(models.Model):
    slug = models.SlugField(max_length=80, unique=True)
    name = models.CharField(max_length=160)
    base_url = models.URLField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["slug"]
        db_table = "providers"

    def __str__(self) -> str:
        return self.name


class ServerOffer(models.Model):
    provider = models.ForeignKey(Provider, related_name="offers", on_delete=models.CASCADE)
    source_offer_id = models.CharField(max_length=220)
    name = models.CharField(max_length=240)
    region = models.CharField(max_length=120, blank=True, null=True)
    country = models.CharField(max_length=120, blank=True, null=True)
    city = models.CharField(max_length=120, blank=True, null=True)
    category = models.CharField(max_length=160, blank=True, null=True)
    billing_period = models.CharField(max_length=40, default="monthly")
    price_amount_irr = models.BigIntegerField(blank=True, null=True)
    original_price_amount = models.BigIntegerField(blank=True, null=True)
    original_price_currency = models.CharField(max_length=40, blank=True, null=True)
    cpu_cores = models.FloatField(blank=True, null=True)
    ram_mb = models.IntegerField(blank=True, null=True)
    disk_gb = models.FloatField(blank=True, null=True)
    disk_type = models.CharField(max_length=80, blank=True, null=True)
    traffic_gb = models.FloatField(blank=True, null=True)
    bandwidth_mbps = models.FloatField(blank=True, null=True)
    has_gpu = models.BooleanField(default=False)
    gpu_model = models.CharField(max_length=160, blank=True, null=True)
    gpu_memory_mb = models.IntegerField(blank=True, null=True)
    available = models.BooleanField(default=True)
    buy_url = models.URLField(max_length=1000, blank=True, null=True)
    source_url = models.URLField(max_length=1000, blank=True, null=True)
    raw_payload = models.JSONField(default=dict)
    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "server_offers"
        ordering = ["price_amount_irr", "provider__slug", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "source_offer_id", "region", "billing_period"],
                name="uq_offer_source_region_period",
            )
        ]
        indexes = [
            models.Index(fields=["provider", "region"], name="offer_provider_region_idx"),
            models.Index(fields=["price_amount_irr"], name="offer_price_idx"),
            models.Index(fields=["has_gpu"], name="offer_gpu_idx"),
            models.Index(fields=["available"], name="offer_available_idx"),
            models.Index(fields=["cpu_cores"], name="offer_cpu_idx"),
            models.Index(fields=["ram_mb"], name="offer_ram_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.provider.slug}: {self.name}"


class CrawlRun(models.Model):
    STATUS_RUNNING = "running"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"

    provider_slug = models.SlugField(max_length=80, db_index=True)
    status = models.CharField(max_length=40, default=STATUS_RUNNING)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(blank=True, null=True)
    fetched_count = models.IntegerField(default=0)
    upserted_count = models.IntegerField(default=0)
    error = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "crawl_runs"
        ordering = ["-started_at"]

    def __str__(self) -> str:
        return f"{self.provider_slug} {self.status} {self.started_at:%Y-%m-%d %H:%M:%S}"
