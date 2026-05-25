from __future__ import annotations

from vps_market.providers.arvancloud import ArvanCloudCrawler
from vps_market.providers.base import ProviderCrawler
from vps_market.providers.iranserver import IranServerCrawler


CRAWLER_TYPES: dict[str, type[ProviderCrawler]] = {
    "iranserver": IranServerCrawler,
    "arvancloud": ArvanCloudCrawler,
}


def get_crawlers(provider_slugs: list[str] | None = None, timeout: int = 30) -> list[ProviderCrawler]:
    slugs = provider_slugs or list(CRAWLER_TYPES)
    unknown = sorted(set(slugs) - set(CRAWLER_TYPES))
    if unknown:
        raise ValueError(f"Unknown provider(s): {', '.join(unknown)}")
    return [CRAWLER_TYPES[slug](timeout=timeout) for slug in slugs]
