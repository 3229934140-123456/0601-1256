import os
import re
from typing import Optional

from .config import IMAGE_EXTENSIONS


def clean_text(text: str) -> str:
    return re.sub(r"\s+", "", text).strip()


def validate_sku(sku: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9]{6,20}", sku))


def parse_price(price_str: str) -> Optional[float]:
    try:
        cleaned = re.sub(r"[^\d.]", "", price_str)
        return float(cleaned) if cleaned else None
    except (ValueError, TypeError):
        return None


def parse_stock(stock_str: str) -> Optional[int]:
    try:
        cleaned = re.sub(r"[^\d]", "", stock_str)
        return int(cleaned) if cleaned else None
    except (ValueError, TypeError):
        return None


def get_file_extension(filename: str) -> str:
    return os.path.splitext(filename)[1].lower()


def is_image_file(filename: str) -> bool:
    return get_file_extension(filename) in IMAGE_EXTENSIONS
