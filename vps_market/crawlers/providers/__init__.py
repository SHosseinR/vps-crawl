from __future__ import annotations

from crawlers.providers.arvancloud import ArvanCloudCrawler
from crawlers.providers.base import ProviderCrawler
from crawlers.providers.ferdowsi_cloud import FerdowsiCloudCrawler
from crawlers.providers.irangpu import IranGpuCrawler
from crawlers.providers.iranserver import IranServerCrawler
from crawlers.providers.lexoya import LexoyaCrawler


CRAWLER_TYPES: dict[str, type[ProviderCrawler]] = {
    "iranserver": IranServerCrawler,
    "arvancloud": ArvanCloudCrawler,
    "irangpu": IranGpuCrawler,
    "lexoya": LexoyaCrawler,
    "ferdowsi_cloud": FerdowsiCloudCrawler,
}


def get_crawlers(
    provider_slugs: list[str] | None = None,
    timeout: int = 30,
    cookies: dict[str, str | None] | None = None,
) -> list[ProviderCrawler]:
    slugs = provider_slugs or list(CRAWLER_TYPES)
    unknown = sorted(set(slugs) - set(CRAWLER_TYPES))
    if unknown:
        raise ValueError(f"Unknown provider(s): {', '.join(unknown)}")
    cookies = cookies or {}
    return [CRAWLER_TYPES[slug](timeout=timeout, cookie=cookies.get(slug)) for slug in slugs]
