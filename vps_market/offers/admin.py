from __future__ import annotations

from django.contrib import admin

from offers.models import CrawlRun, GpuSpec, Provider, ServerOffer


@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ["slug", "name", "base_url", "updated_at"]
    search_fields = ["slug", "name"]


@admin.register(ServerOffer)
class ServerOfferAdmin(admin.ModelAdmin):
    list_display = [
        "provider",
        "name",
        "region",
        "region_detail",
        "billing_period",
        "price_amount_toman",
        "equivalent_hourly_price_toman",
        "has_gpu",
        "available",
    ]
    list_filter = ["provider", "region", "billing_period", "has_gpu", "available"]
    search_fields = ["name", "source_offer_id", "gpu__model", "category", "region_detail"]
    readonly_fields = ["first_seen_at", "last_seen_at", "updated_at", "raw_payload"]


@admin.register(GpuSpec)
class GpuSpecAdmin(admin.ModelAdmin):
    list_display = ["model", "memory_mb", "updated_at"]
    search_fields = ["model", "offers__name"]


@admin.register(CrawlRun)
class CrawlRunAdmin(admin.ModelAdmin):
    list_display = ["provider_slug", "status", "fetched_count", "upserted_count", "started_at", "finished_at"]
    list_filter = ["provider_slug", "status"]
    readonly_fields = ["provider_slug", "status", "started_at", "finished_at", "fetched_count", "upserted_count", "error"]
