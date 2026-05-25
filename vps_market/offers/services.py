from __future__ import annotations

import logging

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


def update_offer_gpu(server_offer: ServerOffer, offer: Offer) -> None:
    if not offer.has_gpu:
        if server_offer.gpu_id:
            server_offer.gpu = None
            server_offer.save(update_fields=["gpu"])
        return

    model = offer.gpu_model or offer.name
    gpu_spec, _ = GpuSpec.objects.get_or_create(
        model=model,
        memory_mb=offer.gpu_memory_mb,
        defaults={
            "raw_payload": {
                "gpu_model": offer.gpu_model,
                "gpu_memory_mb": offer.gpu_memory_mb,
            }
        },
    )
    if gpu_spec.raw_payload != {"gpu_model": offer.gpu_model, "gpu_memory_mb": offer.gpu_memory_mb}:
        gpu_spec.raw_payload = {"gpu_model": offer.gpu_model, "gpu_memory_mb": offer.gpu_memory_mb}
        gpu_spec.save(update_fields=["raw_payload", "updated_at"])

    if server_offer.gpu_id != gpu_spec.id:
        server_offer.gpu = gpu_spec
        server_offer.save(update_fields=["gpu"])


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
