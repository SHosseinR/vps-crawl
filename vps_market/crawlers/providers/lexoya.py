from __future__ import annotations

from typing import Any

from crawlers.providers.base import Offer, ProviderCrawler
from crawlers.utils.text import normalize_text, price_to_irr


class LexoyaCrawler(ProviderCrawler):
    slug = "lexoya"
    display_name = "Lexoya"
    base_url = "https://lexoya.com"
    buy_url = "https://lexoya.com/landings/gpu"
    source_url = "https://lexoya.com/"
    api_urls = (
        "https://api.ir01.lexoya.com/v1/gpus/1005",
        "https://api.ir01.lexoya.com/v1/gpus/1004",
    )

    def crawl(self) -> list[Offer]:
        offers: list[Offer] = []
        for api_url in self.api_urls:
            response = self.get_json(api_url)
            for item in response.get("data") or []:
                if isinstance(item, dict):
                    offers.extend(self._item_to_offers(item, api_url))
        return offers

    def _item_to_offers(self, item: dict[str, Any], api_url: str) -> list[Offer]:
        location = item.get("Location") if isinstance(item.get("Location"), dict) else {}
        source_id = normalize_text(item.get("ID")) or normalize_text(item.get("Name"))
        name = normalize_text(item.get("Name")) or source_id
        city = normalize_text(location.get("name")) or None
        country = normalize_text(location.get("country")) or "Iran"
        available = bool(item.get("IsAvailable")) and normalize_text(item.get("Status")).lower() not in {
            "disabled",
            "unavailable",
        }

        offers: list[Offer] = []
        for billing_period, price_field in (("hourly", "HourlyPrice"), ("monthly", "MonthlyPrice")):
            original_price = item.get(price_field)
            if original_price in {None, ""}:
                continue
            offers.append(
                Offer(
                    source_offer_id=f"{source_id}-{billing_period}",
                    name=name,
                    region="iran",
                    region_detail=(city or "gpu").lower(),
                    country=country,
                    city=city,
                    category="gpu",
                    billing_period=billing_period,
                    price_amount_irr=price_to_irr(int(original_price), "toman"),
                    original_price_amount=int(original_price),
                    original_price_currency="IRT",
                    has_gpu=True,
                    gpu_model=name,
                    gpu_memory_mb=_gb_to_mb(item.get("VramGB")),
                    available=available,
                    buy_url=self.buy_url,
                    source_url=self.source_url,
                    raw_payload=item,
                )
            )
        return offers


def _gb_to_mb(value: object) -> int | None:
    if value in {None, ""}:
        return None
    return int(float(value) * 1024)
