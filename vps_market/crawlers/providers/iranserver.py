from __future__ import annotations

import re
from typing import Any

from crawlers.providers.base import Offer, ProviderCrawler
from crawlers.utils.js_extract import extract_balanced, extract_var_literal, load_json_or_js_literal
from crawlers.utils.specs import extract_specs_from_lines, parse_gpu_memory_mb
from crawlers.utils.text import normalize_digits, normalize_text, parse_int, price_to_irr


class IranServerCrawler(ProviderCrawler):
    slug = "iranserver"
    display_name = "IranServer"
    base_url = "https://www.iranserver.com"
    plans_api_url = "https://www.iranserver.com/pricing/plans"
    gpu_url = "https://www.iranserver.com/vps/gpu/"
    vps_region_urls = {
        "germany": "https://www.iranserver.com/vps/germany/",
        "france": "https://www.iranserver.com/vps/france/",
        "finland": "https://www.iranserver.com/vps/finland/",
        "europe": "https://www.iranserver.com/vps/europe/",
        "usa": "https://www.iranserver.com/vps/usa/",
    }

    def __init__(self, timeout: int = 30, cookie: str | None = None) -> None:
        super().__init__(timeout=timeout, cookie=cookie)
        self.session.headers.update(
            {
                "X-Requested-With": "XMLHttpRequest",
                "Referer": "https://www.iranserver.com/",
            }
        )

    def crawl(self) -> list[Offer]:
        offers: list[Offer] = []
        offers.extend(self.fetch_iran_cloud_api())
        for region, url in self.vps_region_urls.items():
            print(f"Crawling region {region} at {url}")
            offers.extend(self.parse_region_page(region, url, self.get_text(url)))
        offers.extend(self.parse_gpu_page(self.get_text(self.gpu_url)))
        return offers

    def fetch_iran_cloud_api(self) -> list[Offer]:
        offers: list[Offer] = []
        for category_id in range(1, 5):
            page = 1
            while True:
                # body = (
                #     "_token=6ypGk3uxOgr1JCYUir1OeoYEpOdjDxQg2tqPgQGI"
                #     f"&type=cloud&cycle=monthly&category_id={category_id}&page={page}&per_page=20"
                # )
                body = {
                    "_token": "6ypGk3uxOgr1JCYUir1OeoYEpOdjDxQg2tqPgQGI",
                    "type": "cloud",
                    "cycle": "monthly",
                    "category_id": category_id,
                    "page": page,
                    "per_page": 20,
                }
                response = self.post_form_json(self.plans_api_url, body)
                for item in response.get("data") or []:
                    offers.append(self._api_item_to_offer(item, category_id))

                meta = response.get("meta") or {}
                last_page = int(meta.get("last_page") or page)
                if page >= last_page or not response.get("data"):
                    break
                page += 1
        return offers

    def _api_item_to_offer(self, item: dict[str, Any], category_id: int) -> Offer:
        price = item.get("price") or {}
        original_price = parse_int(price.get("value"))
        product_id = item.get("product_id") or item.get("id")
        return Offer(
            source_offer_id=f"cloud-iran-{item.get('id') or product_id}",
            name=normalize_text(item.get("name")) or str(product_id),
            region="iran",
            country="Iran",
            category=f"cloud-category-{category_id}",
            billing_period="monthly",
            price_amount_irr=price_to_irr(original_price, price.get("unit") or "IRT"),
            original_price_amount=original_price,
            original_price_currency=normalize_text(price.get("unit")) or "IRT",
            cpu_cores=_numeric_field(item.get("cpu")),
            ram_mb=_gb_field_to_mb(item.get("ram")),
            disk_gb=_numeric_field(item.get("disk")),
            traffic_gb=_numeric_field(item.get("traffic")),
            has_gpu=False,
            available=True,
            buy_url=f"https://hub.iranserver.com/cart.php?a=add&pid={product_id}" if product_id else None,
            source_url=self.plans_api_url,
            raw_payload=item,
        )

    def parse_region_page(self, region: str, url: str, html_text: str) -> list[Offer]:
        literal = extract_var_literal(html_text, "window.allCardData = {")
        # print('='*50, '\n\n\n')
        # print(literal)
        # print('='*50, '\n\n\n')
        data = load_json_or_js_literal(literal)
        offers: list[Offer] = []

        for group_name, cards in (data or {}).items():
            if not isinstance(cards, list):
                continue
            for card in cards:
                if not isinstance(card, dict):
                    continue
                service_name = normalize_text(card.get("service_name")) or normalize_text(card.get("title"))
                tabs = card.get("tabs") or {}
                for tab_name, tab in tabs.items():
                    if not isinstance(tab, dict):
                        continue
                    offer = self._region_tab_to_offer(
                        region=region,
                        url=url,
                        group_name=str(group_name),
                        tab_name=str(tab_name),
                        service_name=service_name,
                        tab=tab,
                    )
                    if offer:
                        offers.append(offer)

        return offers

    def _region_tab_to_offer(
        self,
        region: str,
        url: str,
        group_name: str,
        tab_name: str,
        service_name: str,
        tab: dict[str, Any],
    ) -> Offer | None:
        prices = tab.get("prices") or {}
        monthly = prices.get("1m") or {}
        original_price = parse_int(monthly.get("price"))
        if original_price is not None and original_price < 0:
            original_price = None

        product_id = tab.get("product_id") or tab.get("id") or f"{service_name}-{group_name}-{tab_name}"
        count = normalize_digits(str(tab.get("count", ""))).lower()
        available = count not in {"0", "false"} and original_price is not None
        feature_lines = [
            normalize_text(feature.get("text"))
            for feature in (tab.get("main_features") or []) + (tab.get("others_features") or [])
            if isinstance(feature, dict)
        ]
        specs = extract_specs_from_lines(feature_lines)

        return Offer(
            source_offer_id=f"vps-{region}-{product_id}-{group_name}-{tab_name}",
            name=service_name or str(product_id),
            region=region,
            country=_country_from_region(region),
            category=group_name if group_name != "others" else tab_name,
            billing_period="monthly",
            price_amount_irr=price_to_irr(original_price, "IRT"),
            original_price_amount=original_price,
            original_price_currency="IRT",
            cpu_cores=specs["cpu_cores"],
            ram_mb=specs["ram_mb"],
            disk_gb=specs["disk_gb"],
            disk_type=specs["disk_type"],
            traffic_gb=specs["traffic_gb"],
            bandwidth_mbps=specs["bandwidth_mbps"],
            has_gpu=False,
            available=available,
            buy_url=f"https://hub.iranserver.com/cart.php?a=add&pid={product_id}" if product_id else None,
            source_url=url,
            raw_payload={"group": group_name, "tab_name": tab_name, "tab": tab, "features": feature_lines},
        )

    def parse_gpu_page(self, html_text: str) -> list[Offer]:
        price_list_literal = extract_var_literal(html_text, "var priceList")
        price_list = load_json_or_js_literal(price_list_literal)
        offers: list[Offer] = []

        for plan_index, billing_period in ((0, "monthly"), (2, "hourly")):
            marker = f"planItems[{plan_index}]"
            marker_index = html_text.find(marker)
            if marker_index < 0:
                continue
            array_start = html_text.find("[", marker_index)
            literal = extract_balanced(html_text, array_start, "[", "]")
            plan_items = load_json_or_js_literal(literal)

            for item in plan_items:
                if not isinstance(item, dict):
                    continue
                offer = self._gpu_item_to_offer(item, price_list, billing_period, plan_index)
                if offer:
                    offers.append(offer)

        return offers

    def _gpu_item_to_offer(
        self,
        item: dict[str, Any],
        price_list: dict[str, Any],
        billing_period: str,
        plan_index: int,
    ) -> Offer | None:
        price_id = str(item.get("price_id") or "")
        monthly_price = _gpu_price(price_list, price_id)
        if monthly_price is not None and monthly_price < 0:
            monthly_price = None
        order_enabled = bool(item.get("orderEnable", False))
        display_enabled = item.get("displayCardEnable", True) is not False
        available = order_enabled and display_enabled and monthly_price is not None
        details = [normalize_text(detail) for detail in item.get("details") or []]
        specs = extract_specs_from_lines(details)
        gpu_line = details[0] if details else normalize_text(item.get("title"))
        gpu_model = _gpu_model(gpu_line, normalize_text(item.get("title")))
        city = _location_from_details(details)

        return Offer(
            source_offer_id=f"gpu-{price_id or item.get('id')}-{billing_period}",
            name=normalize_text(item.get("title")) or str(price_id),
            region="iran-gpu",
            country="Iran",
            city=city,
            category="gpu",
            billing_period=billing_period,
            price_amount_irr=monthly_price,
            original_price_amount=monthly_price,
            original_price_currency="IRR",
            cpu_cores=specs["cpu_cores"],
            ram_mb=specs["ram_mb"],
            disk_gb=specs["disk_gb"],
            disk_type=specs["disk_type"],
            traffic_gb=specs["traffic_gb"],
            bandwidth_mbps=specs["bandwidth_mbps"],
            has_gpu=True,
            gpu_model=gpu_model,
            gpu_memory_mb=parse_gpu_memory_mb(gpu_line),
            available=available,
            buy_url=normalize_text(item.get("orderlink")) or None,
            source_url=self.gpu_url,
            raw_payload={"plan_index": plan_index, "item": item, "details": details},
        )


def _numeric_field(value: dict[str, Any] | None) -> float | None:
    if not isinstance(value, dict):
        return None
    numeric = value.get("value")
    return float(numeric) if numeric is not None else None


def _gb_field_to_mb(value: dict[str, Any] | None) -> int | None:
    numeric = _numeric_field(value)
    return int(numeric * 1024) if numeric is not None else None


def _country_from_region(region: str) -> str | None:
    mapping = {
        "germany": "Germany",
        "france": "France",
        "finland": "Finland",
        "europe": "Europe",
        "usa": "United States",
        "iran": "Iran",
    }
    return mapping.get(region)


def _gpu_price(price_list: dict[str, Any], price_id: str) -> int | None:
    value = price_list.get(price_id)
    if isinstance(value, list) and value:
        value = value[0]
    if not isinstance(value, dict):
        return None
    monthly = value.get("monthly") or {}
    return parse_int(monthly.get("price"))


def _gpu_model(gpu_line: str, fallback: str) -> str | None:
    text = normalize_text(gpu_line)
    match = re.search(r"^([A-Za-z0-9\- ]+?)(?:\(|$)", text)
    if match:
        return match.group(1).strip()
    return fallback or None


def _location_from_details(details: list[str]) -> str | None:
    for detail in details:
        text = normalize_text(detail)
        match = re.search(r"location\s+(.+)$", text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip().title()
    return None
