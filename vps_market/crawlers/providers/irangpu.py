from __future__ import annotations

import re

from bs4 import BeautifulSoup, Tag

from crawlers.providers.base import Offer, ProviderCrawler
from crawlers.utils.specs import extract_specs_from_lines, parse_gpu_memory_mb
from crawlers.utils.text import normalize_digits, normalize_text, parse_int, price_to_irr


class IranGpuCrawler(ProviderCrawler):
    slug = "irangpu"
    display_name = "IranGPU"
    base_url = "https://irangpu.com"
    pricing_url = "https://irangpu.com/rent-gpu-server/"

    def crawl(self) -> list[Offer]:
        return self.parse_pricing_page(self.get_text(self.pricing_url))

    def parse_pricing_page(self, html_text: str) -> list[Offer]:
        soup = BeautifulSoup(html_text, "lxml")
        cards = soup.find_all(_is_plan_card)
        offers: list[Offer] = []

        for index, card in enumerate(cards, start=1):
            offer = self._card_to_offer(card, index)
            if offer:
                offers.append(offer)
        return offers

    def _card_to_offer(self, card: Tag, index: int) -> Offer | None:
        name = _plan_name(card)
        if not name:
            return None

        price_text = _price_text(card)
        original_price = parse_int(price_text)
        billing_period = _billing_period(price_text)
        available = original_price is not None and not _looks_like_consult_price(price_text)
        feature_lines = [
            normalize_text(item.get_text(" ", strip=True))
            for item in card.select(".elementor-icon-list-text")
            if normalize_text(item.get_text(" ", strip=True))
        ]
        gpu_line = _gpu_line(feature_lines) or name
        vm_feature_lines = [line for line in feature_lines if line != gpu_line]
        specs = extract_specs_from_lines(vm_feature_lines)
        city = _city_from_feature_lines(feature_lines)
        button = card.select_one("a.elementor-button-link")
        href = button.get("href") if isinstance(button, Tag) else None
        order_id = button.get("id") if isinstance(button, Tag) else None

        return Offer(
            source_offer_id=order_id or _slugify(name) or f"irangpu-{index}",
            name=name,
            region="iran",
            region_detail=(city or "gpu").lower(),
            country="Iran",
            city=city,
            category="gpu",
            billing_period=billing_period,
            price_amount_irr=price_to_irr(original_price, "toman") if available else None,
            original_price_amount=original_price if available else None,
            original_price_currency="IRT",
            cpu_cores=specs["cpu_cores"],
            ram_mb=specs["ram_mb"],
            disk_gb=specs["disk_gb"],
            disk_type=specs["disk_type"],
            traffic_gb=specs["traffic_gb"],
            bandwidth_mbps=specs["bandwidth_mbps"],
            has_gpu=True,
            gpu_model=_gpu_model(name),
            gpu_memory_mb=parse_gpu_memory_mb(gpu_line),
            available=available,
            buy_url=_absolute_url(href),
            source_url=self.pricing_url,
            raw_payload={"price_text": price_text, "features": feature_lines},
        )


def _is_plan_card(tag) -> bool:
    if not isinstance(tag, Tag) or tag.name != "div":
        return False
    classes = set(tag.get("class") or [])
    return {"e-con-full", "plan-li", "e-flex", "e-con", "e-child"}.issubset(classes)


def _plan_name(card: Tag) -> str:
    title = card.select_one(".plans-title h1, .plans-title h2, .plans-title h3, .plans-title .elementor-heading-title")
    return normalize_text(title.get_text(" ", strip=True)) if title else ""


def _price_text(card: Tag) -> str:
    title = card.select_one(".plans-title")
    for candidate in card.select(".elementor-heading-title"):
        text = normalize_text(candidate.get_text(" ", strip=True))
        if not text or (title and title.find(candidate)):
            continue
        lower = normalize_digits(text).lower()
        if any(marker in lower for marker in ("تومان", "toman", "قیمت", "مشاوره", "ساعتی", "ماه")):
            return text
    return ""


def _billing_period(price_text: str) -> str:
    text = normalize_digits(price_text).lower()
    if "ساعت" in text or "hour" in text:
        return "hourly"
    return "monthly"


def _looks_like_consult_price(price_text: str) -> bool:
    text = normalize_text(price_text)
    return "مشاوره" in text or "تماس" in text or "consult" in text.lower()


def _gpu_line(feature_lines: list[str]) -> str | None:
    for line in feature_lines:
        lower = normalize_digits(line).lower()
        if "vram" in lower:
            return line
    return None


def _gpu_model(name: str) -> str:
    model = name.split("-", 1)[0].strip()
    match = re.search(r"(rtx\s*\d+|l\d+s?|a\d+|h\d+)", model, flags=re.IGNORECASE)
    return match.group(1).replace(" ", "").upper() if match else model


def _city_from_feature_lines(feature_lines: list[str]) -> str | None:
    for line in reversed(feature_lines):
        lower = normalize_digits(line).lower()
        if any(marker in lower for marker in ("cpu", "ram", "vram", "ssd", "hdd", "nvme", "traffic", "bandwidth", "gb", "tb")):
            continue
        return normalize_text(line).title()
    return None


def _absolute_url(href: str | None) -> str | None:
    if not href or href == "#":
        return None
    if href.startswith("http"):
        return href
    return f"https://irangpu.com/{href.lstrip('/')}"


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", normalize_digits(value).lower()).strip("-")
    return slug
