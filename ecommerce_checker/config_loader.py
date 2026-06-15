from __future__ import annotations

import copy
import json
import os
from typing import Any, Dict, List, Optional

try:
    import yaml
    _YAML_AVAILABLE = True
except ImportError:
    _YAML_AVAILABLE = False

from .config import (
    CATEGORY_RULES,
    DETAIL_IMAGES_MIN_COUNT,
    IMAGE_EXTENSIONS,
    IMAGE_MAX_SIZE_MB,
    IMAGE_MIN_HEIGHT,
    IMAGE_MIN_WIDTH,
    PRICE_MAX,
    PRICE_MIN,
    SENSITIVE_WORDS,
    TITLE_MAX_LENGTH,
)


CONFIG_FILENAMES = [
    "checker_config.yaml",
    "checker_config.yml",
    "checker_config.json",
    ".checker_config.yaml",
    ".checker_config.yml",
    ".checker_config.json",
]


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and key in result and isinstance(result[key], dict):
            result[key] = _deep_merge(result[key], value)
        elif isinstance(value, list) and key in result and isinstance(result[key], list):
            result[key] = list(result[key]) + list(value)
        else:
            result[key] = value
    return result


class CheckerConfig:
    def __init__(self, folder_path: str):
        self.folder_path = folder_path
        self._global_config: Dict[str, Any] = self._get_default_config()
        self._shop_configs: Dict[str, Dict[str, Any]] = {}
        self._load_config_file()

    def _get_default_config(self) -> Dict[str, Any]:
        return {
            "title_max_length": TITLE_MAX_LENGTH,
            "price_min": PRICE_MIN,
            "price_max": PRICE_MAX,
            "sensitive_words": list(SENSITIVE_WORDS),
            "detail_images_min_count": DETAIL_IMAGES_MIN_COUNT,
            "image_min_width": IMAGE_MIN_WIDTH,
            "image_min_height": IMAGE_MIN_HEIGHT,
            "image_max_size_mb": IMAGE_MAX_SIZE_MB,
            "image_extensions": list(IMAGE_EXTENSIONS),
            "category_rules": copy.deepcopy(CATEGORY_RULES),
        }

    def _load_config_file(self) -> None:
        config_file = self._find_config_file()
        if not config_file:
            return

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                if config_file.endswith(".json"):
                    data = json.load(f)
                elif _YAML_AVAILABLE:
                    data = yaml.safe_load(f)
                else:
                    data = {}
        except Exception:
            return

        if "global" in data and isinstance(data["global"], dict):
            self._global_config = _deep_merge(self._global_config, data["global"])

        if "shops" in data and isinstance(data["shops"], dict):
            for shop_name, shop_overrides in data["shops"].items():
                if isinstance(shop_overrides, dict):
                    self._shop_configs[shop_name] = _deep_merge(
                        self._global_config, shop_overrides
                    )

    def _find_config_file(self) -> Optional[str]:
        for filename in CONFIG_FILENAMES:
            filepath = os.path.join(self.folder_path, filename)
            if os.path.isfile(filepath):
                return filepath
        return None

    def get(self, key: str, shop: Optional[str] = None) -> Any:
        if shop and shop in self._shop_configs:
            if key in self._shop_configs[shop]:
                return self._shop_configs[shop][key]
        return self._global_config.get(key)

    def get_config_for_shop(self, shop: Optional[str]) -> Dict[str, Any]:
        if shop and shop in self._shop_configs:
            return copy.deepcopy(self._shop_configs[shop])
        return copy.deepcopy(self._global_config)

    @property
    def has_custom_config(self) -> bool:
        return self._find_config_file() is not None

    @property
    def configured_shops(self) -> List[str]:
        return list(self._shop_configs.keys())

    @property
    def config_file_path(self) -> Optional[str]:
        return self._find_config_file()

    @property
    def global_config(self) -> Dict[str, Any]:
        return copy.deepcopy(self._global_config)

    @property
    def shop_configs(self) -> Dict[str, Dict[str, Any]]:
        return {k: copy.deepcopy(v) for k, v in self._shop_configs.items()}

    def get_all_shops_with_config(self) -> List[str]:
        shops = set(self._shop_configs.keys())
        return sorted(shops)

    def get_effective_config(self, shop: Optional[str]) -> Dict[str, Any]:
        return self.get_config_for_shop(shop)


def load_config(folder_path: str) -> CheckerConfig:
    return CheckerConfig(folder_path)
