from __future__ import annotations

import logging
import re
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from crawlers.providers import get_crawlers
from crawlers.providers.base import Offer, ProviderCrawler
from offers.models import CrawlRun, GpuSpec, Provider, ServerOffer


logger = logging.getLogger(__name__)


def ensure_provider(crawler: ProviderCrawler) -> Provider:
    provider, _ = Provider.objects.update_or_create(
        slug=crawler.slug,
        defaults={"name": crawler.display_name, "base_url": crawler.base_url},
    )
    return provider


def crawl_once(
    provider_slugs: list[str] | None = None,
    timeout: int = 30,
    cookies: dict[str, str | None] | None = None,
) -> dict[str, int]:
    summary: dict[str, int] = {}
    for crawler in get_crawlers(provider_slugs=provider_slugs, timeout=timeout, cookies=cookies):
        summary[crawler.slug] = crawl_provider(crawler)
    return summary


def crawl_provider(crawler: ProviderCrawler) -> int:
    run = CrawlRun.objects.create(provider_slug=crawler.slug, status=CrawlRun.STATUS_RUNNING)
    try:
        logger.info("Crawling provider=%s", crawler.slug)
        offers = crawler.crawl()
        seen_at = timezone.now()
        with transaction.atomic():
            provider = ensure_provider(crawler)
            upserted = upsert_offers(provider, offers, seen_at)
            if offers:
                mark_missing_offers_unavailable(provider, seen_at)
            finish_run(run, CrawlRun.STATUS_SUCCESS, len(offers), upserted)
        logger.info("Crawled provider=%s fetched=%s upserted=%s", crawler.slug, len(offers), upserted)
        return len(offers)
    except Exception as exc:
        logger.exception("Provider crawl failed provider=%s", crawler.slug)
        finish_run(run, CrawlRun.STATUS_FAILED, 0, 0, str(exc))
        return 0


def upsert_offers(provider: Provider, offers: list[Offer], seen_at) -> int:
    upserted = 0
    for offer in offers:
        defaults = offer_defaults(offer, seen_at)
        server_offer, _ = ServerOffer.objects.update_or_create(
            provider=provider,
            source_offer_id=offer.source_offer_id,
            region=offer.region,
            region_detail=offer.region_detail or "",
            billing_period=offer.billing_period,
            defaults=defaults,
        )
        update_offer_gpu(server_offer, offer)
        upserted += 1
    return upserted


def offer_defaults(offer: Offer, seen_at) -> dict[str, object]:
    return {
        "name": offer.name,
        "country": offer.country,
        "city": offer.city,
        "category": offer.category,
        "price_amount_irr": offer.price_amount_irr,
        "price_amount_toman": price_amount_toman(offer.price_amount_irr),
        "equivalent_hourly_price_toman": equivalent_hourly_price_toman(
            offer.price_amount_irr,
            offer.billing_period,
        ),
        "original_price_amount": offer.original_price_amount,
        "original_price_currency": offer.original_price_currency,
        "cpu_cores": offer.cpu_cores,
        "ram_mb": offer.ram_mb,
        "disk_gb": offer.disk_gb,
        "disk_type": offer.disk_type,
        "traffic_gb": offer.traffic_gb,
        "bandwidth_mbps": offer.bandwidth_mbps,
        "has_gpu": offer.has_gpu,
        "available": offer.available,
        "buy_url": offer.buy_url,
        "source_url": offer.source_url,
        "raw_payload": offer.raw_payload,
        "last_seen_at": seen_at,
    }


def price_amount_toman(price_amount_irr: int | None) -> int | None:
    if price_amount_irr is None:
        return None
    return int(Decimal(price_amount_irr) / Decimal("10"))


def equivalent_hourly_price_toman(price_amount_irr: int | None, billing_period: str | None) -> Decimal | None:
    toman = price_amount_toman(price_amount_irr)
    if toman is None:
        return None

    period_hours = {
        "hour": Decimal("1"),
        "hourly": Decimal("1"),
        "day": Decimal("24"),
        "daily": Decimal("24"),
        "week": Decimal("168"),
        "weekly": Decimal("168"),
        "month": Decimal("720"),
        "monthly": Decimal("720"),
        "year": Decimal("8760"),
        "yearly": Decimal("8760"),
        "annual": Decimal("8760"),
        "annually": Decimal("8760"),
    }
    hours = period_hours.get((billing_period or "").lower(), Decimal("720"))
    return (Decimal(toman) / hours).quantize(Decimal("0.01"))


def update_offer_gpu(server_offer: ServerOffer, offer: Offer) -> None:
    if not offer.has_gpu:
        if server_offer.gpu_id:
            server_offer.gpu = None
            server_offer.save(update_fields=["gpu"])
        return

    model = normalize_gpu_model_name(offer.gpu_model or offer.name)
    gpu_spec = get_or_create_gpu_spec(model, offer.gpu_memory_mb)
    raw_payload = {
        "gpu_model": offer.gpu_model,
        "normalized_model": model,
        "gpu_memory_mb": offer.gpu_memory_mb,
    }
    if gpu_spec.raw_payload != raw_payload:
        gpu_spec.raw_payload = raw_payload
        gpu_spec.save(update_fields=["raw_payload", "updated_at"])

    if server_offer.gpu_id != gpu_spec.id:
        server_offer.gpu = gpu_spec
        server_offer.save(update_fields=["gpu"])


def normalize_gpu_model_name(model: str | None) -> str:
    normalized = (model or "").strip()
    normalized = re.sub(r"^\s*nvidia[\s\-_]+", "", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\s*\([^)]*\)\s*$", "", normalized).strip()
    normalized = normalized.replace("-", " ").replace("_", " ")
    normalized = re.sub(r"\bRTX(?=\d)", "RTX ", normalized, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", normalized).strip() or "Unknown GPU"


def get_or_create_gpu_spec(model: str, memory_mb: int | None) -> GpuSpec:
    if memory_mb is None:
        existing_with_memory = find_gpu_spec(model, memory="known")
        if existing_with_memory:
            return update_gpu_spec_identity(existing_with_memory, model)

        null_memory_spec = find_gpu_spec(model, memory=None)
        if null_memory_spec:
            return update_gpu_spec_identity(null_memory_spec, model)

        return GpuSpec.objects.create(model=model, memory_mb=None)

    exact = find_gpu_spec(model, memory=memory_mb)
    if exact:
        return update_gpu_spec_identity(exact, model)

    null_memory_spec = find_gpu_spec(model, memory=None)
    if null_memory_spec:
        null_memory_spec.model = model
        null_memory_spec.memory_mb = memory_mb
        null_memory_spec.save(update_fields=["model", "memory_mb", "updated_at"])
        return null_memory_spec

    return GpuSpec.objects.create(model=model, memory_mb=memory_mb)


def find_gpu_spec(model: str, memory: int | str | None) -> GpuSpec | None:
    if memory == "known":
        queryset = GpuSpec.objects.filter(memory_mb__isnull=False).order_by("memory_mb", "id")
    elif memory is None:
        queryset = GpuSpec.objects.filter(memory_mb__isnull=True).order_by("id")
    else:
        queryset = GpuSpec.objects.filter(memory_mb=memory).order_by("id")

    key = gpu_model_key(model)
    for gpu_spec in queryset:
        if gpu_model_key(gpu_spec.model) == key:
            return gpu_spec
    return None


def update_gpu_spec_identity(gpu_spec: GpuSpec, model: str) -> GpuSpec:
    if gpu_spec.model != model:
        gpu_spec.model = model
        gpu_spec.save(update_fields=["model", "updated_at"])
    return gpu_spec


def gpu_model_key(model: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", model.lower())


def mark_missing_offers_unavailable(provider: Provider, seen_at) -> int:
    return (
        ServerOffer.objects.filter(provider=provider, last_seen_at__lt=seen_at)
        .update(available=False, updated_at=timezone.now())
    )


def finish_run(
    run: CrawlRun,
    status: str,
    fetched_count: int,
    upserted_count: int,
    error: str | None = None,
) -> None:
    run.status = status
    run.fetched_count = fetched_count
    run.upserted_count = upserted_count
    run.error = error
    run.finished_at = timezone.now()
    run.save(update_fields=["status", "fetched_count", "upserted_count", "error", "finished_at"])
