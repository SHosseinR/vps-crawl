from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import requests
from tenacity import retry, stop_after_attempt, wait_exponential


@dataclass(slots=True)
class Offer:
    source_offer_id: str
    name: str
    billing_period: str
    price_amount_irr: int | None
    original_price_amount: int | None
    original_price_currency: str | None
    region: str | None = None
    region_detail: str | None = None
    country: str | None = None
    city: str | None = None
    category: str | None = None
    cpu_cores: float | None = None
    ram_mb: int | None = None
    disk_gb: float | None = None
    disk_type: str | None = None
    traffic_gb: float | None = None
    bandwidth_mbps: float | None = None
    has_gpu: bool = False
    gpu_model: str | None = None
    gpu_memory_mb: int | None = None
    available: bool = True
    buy_url: str | None = None
    source_url: str | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict)


class ProviderCrawler:
    slug: str
    display_name: str
    base_url: str

    def __init__(self, timeout: int = 30, cookie: str | None = None) -> None:
        self.timeout = timeout
        self.cookie = cookie
        self.session = requests.Session()
        # self.session.headers.update(
        #     {
        #         "User-Agent": (
        #             "Mozilla/5.0 (compatible; VPSMarketCrawler/0.1; "
        #             "+https://example.local/vps-market)"
        #         ),
        #         "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
        #     }
        # )

    def crawl(self) -> list[Offer]:
        raise NotImplementedError

    def _headers(self, cookie: str | None = None, extra: dict[str, str] | None = None) -> dict[str, str]:
        headers = dict(extra or {})
        request_cookie = cookie or self.cookie
        if request_cookie:
            headers["Cookie"] = request_cookie
        return headers

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    def get_text(self, url: str, cookie: str | None = None) -> str:
        response = self.session.get(url, headers=self._headers(cookie), timeout=self.timeout)
        response.raise_for_status()
        response.encoding = response.apparent_encoding or response.encoding
        return response.text

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    def post_form_json(self, url: str, body: str, cookie: str | None = None) -> dict[str, Any]:
        response = self.session.post(
            url,
            data=body,
            headers=self._headers(cookie, {"Content-Type": "application/x-www-form-urlencoded"}),
            timeout=self.timeout,
        )
        # print(f'{url=}, {body=}, {response.status_code=}, {response.text[:200]=}')
        response.raise_for_status()
        return response.json()
