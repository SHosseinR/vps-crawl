from __future__ import annotations

import re

from crawlers.utils.text import normalize_digits, normalize_text, parse_float


def gb_to_mb(value: float | None) -> int | None:
    return int(value * 1024) if value is not None else None


def parse_cpu(text: str | None) -> float | None:
    value = normalize_digits(text).lower()
    patterns = [
        r"(\d+(?:\.\d+)?)\s*(?:v\s*)?cores?",
        r"cpu\s*(\d+(?:\.\d+)?)",
        r"(\d+(?:\.\d+)?)\s*cpu",
    ]
    for pattern in patterns:
        match = re.search(pattern, value)
        if match:
            return float(match.group(1))
    return None


def parse_memory_mb(text: str | None) -> int | None:
    value = normalize_digits(text).lower()
    match = re.search(r"(\d+(?:\.\d+)?)\s*(tb|ترا(?:بایت)?|gb|گیگ(?:ابایت)?)", value)
    if not match:
        return None
    amount = float(match.group(1))
    unit = match.group(2)
    if unit.startswith("tb") or unit.startswith("ترا"):
        amount *= 1024
    return gb_to_mb(amount)


def parse_storage_gb(text: str | None) -> tuple[float | None, str | None]:
    value = normalize_digits(text).lower()
    match = re.search(r"(\d+(?:\.\d+)?)\s*(tb|ترا(?:بایت)?|gb|گیگ(?:ابایت)?)", value)
    amount = None
    if match:
        amount = float(match.group(1))
        unit = match.group(2)
        if unit.startswith("tb") or unit.startswith("ترا"):
            amount *= 1024
    disk_type = None
    for candidate in ("nvme", "ssd", "hdd"):
        if candidate in value:
            disk_type = candidate.upper()
            break
    return amount, disk_type


def parse_traffic_gb(text: str | None) -> float | None:
    value = normalize_digits(text).lower()
    if "traffic" not in value and "ترافیک" not in value:
        return None
    amount = parse_float(value)
    if amount is None:
        return None
    if "tb" in value or "ترا" in value:
        return amount * 1024
    return amount


def parse_bandwidth_mbps(text: str | None) -> float | None:
    value = normalize_digits(text).lower()
    if "bandwidth" not in value and "port" not in value and "پورت" not in value:
        return None
    amount = parse_float(value)
    if amount is None:
        return None
    if "gb" in value or "gbit" in value or "گیگ" in value:
        return amount * 1024
    if "mb/s" in value or "mbyte" in value:
        return amount * 8
    return amount


def parse_gpu_memory_mb(text: str | None) -> int | None:
    value = normalize_digits(text).lower()
    match = re.search(r"(?:ram)?\s*(\d+(?:\.\d+)?)\s*gb", value)
    return gb_to_mb(float(match.group(1))) if match else None


def extract_specs_from_lines(lines: list[str]) -> dict[str, object]:
    specs: dict[str, object] = {
        "cpu_cores": None,
        "ram_mb": None,
        "disk_gb": None,
        "disk_type": None,
        "traffic_gb": None,
        "bandwidth_mbps": None,
    }

    for line in lines:
        text = normalize_text(line)
        lower = normalize_digits(text).lower()
        if specs["cpu_cores"] is None:
            specs["cpu_cores"] = parse_cpu(text)
        if specs["ram_mb"] is None and ("ram" in lower or "رم" in lower or "memory" in lower):
            specs["ram_mb"] = parse_memory_mb(text)
        if specs["disk_gb"] is None and any(marker in lower for marker in ("ssd", "hdd", "nvme", "disk", "فضا")):
            disk_gb, disk_type = parse_storage_gb(text)
            specs["disk_gb"] = disk_gb
            specs["disk_type"] = disk_type
        if specs["traffic_gb"] is None:
            specs["traffic_gb"] = parse_traffic_gb(text)
        if specs["bandwidth_mbps"] is None:
            specs["bandwidth_mbps"] = parse_bandwidth_mbps(text)

    return specs
