from __future__ import annotations

import json
import os
from datetime import datetime
from typing import List, Optional

from .models import BaselineRecord, CheckResult, ScanResult

BASELINE_DIR = ".ecommerce_checker"
BASELINE_FILE = "baseline.json"


def _baseline_path(folder_path: str) -> str:
    d = os.path.join(folder_path, BASELINE_DIR)
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, BASELINE_FILE)


def save_baseline(folder_path: str, scan_result: ScanResult, check_results: List[CheckResult]) -> BaselineRecord:
    critical = sum(1 for r in check_results for i in r.issues if i.level == "critical")
    warning = sum(1 for r in check_results for i in r.issues if i.level == "warning")
    info = sum(1 for r in check_results for i in r.issues if i.level == "info")
    passed = sum(1 for r in check_results if r.passed)
    failed = len(check_results) - passed

    record = BaselineRecord(
        timestamp=datetime.now().isoformat(),
        total_files=scan_result.total_files,
        total_products=scan_result.total_products,
        stores=scan_result.stores,
        categories=scan_result.categories,
        total_issues=critical + warning + info,
        critical_count=critical,
        warning_count=warning,
        info_count=info,
        passed_count=passed,
        failed_count=failed,
    )

    path = _baseline_path(folder_path)
    data = {
        "timestamp": record.timestamp,
        "total_files": record.total_files,
        "total_products": record.total_products,
        "stores": record.stores,
        "categories": record.categories,
        "total_issues": record.total_issues,
        "critical_count": record.critical_count,
        "warning_count": record.warning_count,
        "info_count": record.info_count,
        "passed_count": record.passed_count,
        "failed_count": record.failed_count,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return record


def load_baseline(folder_path: str) -> Optional[BaselineRecord]:
    path = _baseline_path(folder_path)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return BaselineRecord(
            timestamp=data.get("timestamp", ""),
            total_files=data.get("total_files", 0),
            total_products=data.get("total_products", 0),
            stores=data.get("stores", []),
            categories=data.get("categories", []),
            total_issues=data.get("total_issues", 0),
            critical_count=data.get("critical_count", 0),
            warning_count=data.get("warning_count", 0),
            info_count=data.get("info_count", 0),
            passed_count=data.get("passed_count", 0),
            failed_count=data.get("failed_count", 0),
        )
    except Exception:
        return None


def build_current_record(scan_result: ScanResult, check_results: List[CheckResult]) -> BaselineRecord:
    critical = sum(1 for r in check_results for i in r.issues if i.level == "critical")
    warning = sum(1 for r in check_results for i in r.issues if i.level == "warning")
    info = sum(1 for r in check_results for i in r.issues if i.level == "info")
    passed = sum(1 for r in check_results if r.passed)
    failed = len(check_results) - passed

    return BaselineRecord(
        timestamp=datetime.now().isoformat(),
        total_files=scan_result.total_files,
        total_products=scan_result.total_products,
        stores=scan_result.stores,
        categories=scan_result.categories,
        total_issues=critical + warning + info,
        critical_count=critical,
        warning_count=warning,
        info_count=info,
        passed_count=passed,
        failed_count=failed,
    )
