from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Product:
    sku: str
    title: str = ""
    price: Optional[float] = None
    stock: Optional[int] = None
    category: str = ""
    shop: str = ""
    main_image: Optional[str] = None
    detail_images: List[str] = field(default_factory=list)
    source_file: str = ""
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScanResult:
    products: List[Product] = field(default_factory=list)
    total_files: int = 0
    total_products: int = 0
    stores: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


@dataclass
class CheckIssue:
    sku: str
    field: str
    issue_type: str
    message: str
    level: str
    suggestion: Optional[str] = None
    auto_fixable: bool = False
    fixed_value: Optional[Any] = None


@dataclass
class CheckResult:
    product: Product
    issues: List[CheckIssue] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return len(self.issues) == 0


@dataclass
class FixPreview:
    sku: str
    field: str
    old_value: Any
    new_value: Any
    reason: str


@dataclass
class BaselineRecord:
    timestamp: str
    total_files: int
    total_products: int
    stores: List[str]
    categories: List[str]
    total_issues: int
    critical_count: int
    warning_count: int
    info_count: int
    passed_count: int
    failed_count: int
