from __future__ import annotations

from typing import Any

from crawlers.providers.base import Offer, ProviderCrawler
from crawlers.utils.text import normalize_text


class FerdowsiCloudCrawler(ProviderCrawler):
    slug = "ferdowsi_cloud"
    display_name = "Ferdowsi Cloud"
    base_url = "https://ferdowsi.cloud"
    buy_url = "https://ferdowsi.cloud/fa/services/gpu"
    source_url = "https://ferdowsi.cloud"
    gpu_list_url = "https://api.ferdowsi.cloud/api/v2/sm/mhd-fum1/flavors/gpus"
    flavors_url = "https://api.ferdowsi.cloud/api/v2/planning/mhd-fum1/flavors"

    def crawl(self) -> list[Offer]:
        response = self.get_json(self.gpu_list_url)
        gpu_items = [item for item in response.get("data") or [] if isinstance(item, dict)]

        offers: list[Offer] = []
        for gpu_item in gpu_items:
            gpu_name = normalize_text(gpu_item.get("name"))
            if not gpu_name:
                continue
            flavors = self.get_json(
                self.flavors_url,
                params={"type": "GPU", "public": "True", "gpu_name": gpu_name},
            )
            offers.extend(self._flavors_to_offers(gpu_item, flavors))
        return offers

    def _flavors_to_offers(self, gpu_item: dict[str, Any], response: dict[str, Any]) -> list[Offer]:
        data = response.get("data") if isinstance(response.get("data"), dict) else {}
        plans = [plan for plan in data.get("plans") or [] if isinstance(plan, dict)]
        offers: list[Offer] = []

        for plan in plans:
            price_amount_irr = _hourly_rating(plan.get("ratings"))
            if price_amount_irr is not None:
                offers.append(self._plan_to_offer(gpu_item, plan, "hourly", price_amount_irr))
        return offers

    def _plan_to_offer(
        self,
        gpu_item: dict[str, Any],
        plan: dict[str, Any],
        billing_period: str,
        price_amount_irr: int,
    ) -> Offer:
        plan_id = normalize_text(plan.get("id")) or normalize_text(plan.get("name"))
        gpu_name = normalize_text(plan.get("gpu_name")) or normalize_text(gpu_item.get("name"))
        region_detail = normalize_text(plan.get("region")) or "mhd-fum1"
        gpu_count = _int_or_none(plan.get("gpu_count")) or 1
        gpu_memory_mb = _gb_to_mb(gpu_item.get("memory"))
        gpu_model = _display_gpu_model(gpu_item, gpu_name, gpu_count)

        return Offer(
            source_offer_id=f"{plan_id}-{billing_period}",
            name=normalize_text(plan.get("name")) or gpu_model,
            region="iran",
            region_detail=region_detail.lower(),
            country="Iran",
            city=_city_from_region(region_detail),
            category="gpu",
            billing_period=billing_period,
            price_amount_irr=price_amount_irr,
            original_price_amount=price_amount_irr,
            original_price_currency="IRR",
            cpu_cores=_nested_float(plan, "cpu", "cores"),
            ram_mb=_memory_to_mb(plan.get("ram")),
            disk_gb=_nested_float(plan, "disk", "size"),
            disk_type=normalize_text(plan.get("disk_type")).upper() or None,
            bandwidth_mbps=_bandwidth_mbps(plan.get("bandwidth")),
            has_gpu=True,
            gpu_model=gpu_model,
            gpu_memory_mb=gpu_memory_mb * gpu_count if gpu_memory_mb is not None else None,
            available=not bool(plan.get("busy")) and not bool(gpu_item.get("busy")),
            buy_url=self.buy_url,
            source_url=self.source_url,
            raw_payload={"gpu": gpu_item, "plan": plan},
        )


def _hourly_rating(ratings: object) -> int | None:
    if not isinstance(ratings, dict):
        return None
    value = ratings.get("hourly")
    if value in {None, ""}:
        return None
    return int(value)


def _display_gpu_model(gpu_item: dict[str, Any], gpu_name: str, gpu_count: int) -> str:
    display_name = normalize_text(gpu_item.get("display_name")) or gpu_name
    if gpu_count > 1:
        return f"{display_name} x{gpu_count}"
    return display_name


def _nested_float(item: dict[str, Any], key: str, nested_key: str) -> float | None:
    value = item.get(key)
    if not isinstance(value, dict):
        return None
    nested_value = value.get(nested_key)
    if nested_value in {None, "", "unlimited"}:
        return None
    return float(nested_value)


def _memory_to_mb(value: object) -> int | None:
    if not isinstance(value, dict):
        return None
    size = value.get("size")
    if size in {None, ""}:
        return None
    unit = normalize_text(value.get("unit")).lower()
    amount = float(size)
    if unit == "gb":
        amount *= 1024
    return int(amount)


def _gb_to_mb(value: object) -> int | None:
    if value in {None, ""}:
        return None
    return int(float(value) * 1024)


def _bandwidth_mbps(value: object) -> float | None:
    if not isinstance(value, dict):
        return None
    size = value.get("size")
    if size in {None, "", "unlimited"}:
        return None
    unit = normalize_text(value.get("unit")).lower()
    amount = float(size)
    if unit in {"gbps", "gbit", "gb/s"}:
        return amount * 1024
    return amount


def _int_or_none(value: object) -> int | None:
    if value in {None, ""}:
        return None
    return int(value)


def _city_from_region(region: str) -> str | None:
    normalized = normalize_text(region).lower()
    if normalized.startswith("mhd-"):
        return "Mashhad"
    return None
