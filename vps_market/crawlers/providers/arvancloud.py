from __future__ import annotations

import html
import re
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup, Tag

from crawlers.providers.base import Offer, ProviderCrawler
from crawlers.utils.specs import parse_cpu, parse_memory_mb, parse_storage_gb
from crawlers.utils.text import normalize_digits, normalize_text, parse_int, price_to_irr


class ArvanCloudCrawler(ProviderCrawler):
    slug = "arvancloud"
    display_name = "ArvanCloud"
    base_url = "https://www.arvancloud.ir"
    pricing_url = "https://www.arvancloud.ir/fa/products/vps"

    def crawl(self) -> list[Offer]:
        html_text = self.get_text(self.pricing_url)
        return self.parse_pricing_page(html_text)

    def parse_pricing_page(self, html_text: str) -> list[Offer]:
        soup = BeautifulSoup(html_text, "lxml")
        tables = soup.find_all(_is_pricing_table_container)
        offers: list[Offer] = []

        for table_index, container in enumerate(tables, start=1):
            category = _find_category(container) or f"table-{table_index}"
            for row in container.select("tbody tr[onclick]"):
                cells = [normalize_text(cell.get_text(" ", strip=True)) for cell in row.find_all("td")]
                if len(cells) < 5:
                    continue

                buy_url = _extract_onclick_url(row.get("onclick", ""))
                name, cpu_text, ram_text, disk_text, price_text = cells[:5]
                original_price = parse_int(price_text)
                disk_gb, disk_type = parse_storage_gb(disk_text)
                az = _query_value(buy_url, "az")
                city = _city_from_az(az)

                offers.append(
                    Offer(
                        source_offer_id=_query_value(buy_url, "size") or name,
                        name=name,
                        region=az or "iran",
                        country="Iran",
                        city=city,
                        category=category,
                        billing_period="monthly",
                        price_amount_irr=price_to_irr(original_price, "IRT"),
                        original_price_amount=original_price,
                        original_price_currency="IRT",
                        cpu_cores=parse_cpu(cpu_text),
                        ram_mb=parse_memory_mb(ram_text),
                        disk_gb=disk_gb,
                        disk_type=disk_type,
                        has_gpu=False,
                        available=True,
                        buy_url=buy_url,
                        source_url=self.pricing_url,
                        raw_payload={
                            "cells": cells,
                            "onclick": row.get("onclick"),
                            "table_index": table_index,
                        },
                    )
                )

        return offers


def _is_pricing_table_container(tag) -> bool:
    if not isinstance(tag, Tag) or tag.name != "div":
        return False
    classes = tag.get("class") or []
    return "xl:overflow-hidden" in classes and "overflow-x-auto" in classes and "rounded-t-lg" in classes


def _find_category(container: Tag) -> str | None:
    heading = container.find_previous(["h2", "h3", "h4"])
    return normalize_text(heading.get_text(" ", strip=True)) if heading else None


def _extract_onclick_url(onclick: str) -> str | None:
    match = re.search(r"window\.open\('([^']+)'", onclick)
    return html.unescape(match.group(1)) if match else None


def _query_value(url: str | None, name: str) -> str | None:
    if not url:
        return None
    values = parse_qs(urlparse(url).query).get(name)
    return values[0] if values else None


def _city_from_az(az: str | None) -> str | None:
    if not az:
        return None
    normalized = normalize_digits(az).lower()
    if normalized.startswith("ir-thr"):
        return "Tehran"
    if normalized.startswith("ir-"):
        return "Iran"
    return None
