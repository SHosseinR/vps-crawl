from __future__ import annotations

import re


PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def repair_mojibake(value: str | None) -> str:
    if not value:
        return ""
    text = str(value)
    if any(marker in text for marker in ("Ù", "Ø", "Û", "Ú", "â")):
        for encoding in ("latin1", "cp1252"):
            try:
                return text.encode(encoding).decode("utf-8")
            except UnicodeError:
                continue
    return text


def normalize_text(value: str | None) -> str:
    text = repair_mojibake(value)
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def normalize_digits(value: str | None) -> str:
    return normalize_text(value).translate(PERSIAN_DIGITS)


def parse_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    text = normalize_digits(str(value))
    text = re.sub(r"[^\d\-]", "", text)
    if not text or text == "-":
        return None
    return int(text)


def parse_float(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, int | float):
        return float(value)
    text = normalize_digits(str(value)).replace(",", "")
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    return float(match.group(0)) if match else None


def price_to_irr(amount: int | None, currency: str | None) -> int | None:
    if amount is None:
        return None
    normalized = normalize_text(currency).lower()
    if normalized in {"toman", "irt", "تومان"} or "تومان" in normalized:
        return amount * 10
    return amount
