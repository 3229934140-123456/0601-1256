from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd

from .models import BaselineRecord, CheckResult, ScanResult

BASELINE_DIR = ".ecommerce_checker"
BASELINE_FILE = "baseline.json"
HISTORY_FILE = "history.json"
MAX_HISTORY = 50

TOOL_MARKER_SHEET = "__ecommerce_checker__"


def _baseline_dir(folder_path: str) -> str:
    d = os.path.join(folder_path, BASELINE_DIR)
    os.makedirs(d, exist_ok=True)
    return d


def _baseline_path(folder_path: str) -> str:
    return os.path.join(_baseline_dir(folder_path), BASELINE_FILE)


def _history_path(folder_path: str) -> str:
    return os.path.join(_baseline_dir(folder_path), HISTORY_FILE)


def _record_to_dict(record: BaselineRecord) -> Dict:
    return {
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


def _dict_to_record(data: Dict) -> BaselineRecord:
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


def save_baseline(folder_path: str, scan_result: ScanResult, check_results: List[CheckResult]) -> BaselineRecord:
    record = build_current_record(scan_result, check_results)
    path = _baseline_path(folder_path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(_record_to_dict(record), f, ensure_ascii=False, indent=2)
    return record


def load_baseline(folder_path: str) -> Optional[BaselineRecord]:
    path = _baseline_path(folder_path)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return _dict_to_record(data)
    except Exception:
        return None


def add_history(folder_path: str, record: BaselineRecord) -> None:
    path = _history_path(folder_path)
    history = []
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []

    history.append(_record_to_dict(record))
    history = history[-MAX_HISTORY:]

    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def load_history(folder_path: str, limit: int = 10) -> List[BaselineRecord]:
    path = _history_path(folder_path)
    if not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            history = json.load(f)
        records = [_dict_to_record(d) for d in history]
        return records[-limit:]
    except Exception:
        return []


def export_history(folder_path: str, output_path: str, limit: int = 50) -> str:
    history = load_history(folder_path, limit=limit)
    if not history:
        raise RuntimeError("没有历史记录可导出")

    data = []
    for idx, record in enumerate(reversed(history)):
        try:
            dt = datetime.fromisoformat(record.timestamp)
            time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            time_str = record.timestamp

        data.append({
            "序号": len(history) - idx,
            "检查时间": time_str,
            "商品文件数": record.total_files,
            "商品总数": record.total_products,
            "通过检查": record.passed_count,
            "存在问题": record.failed_count,
            "问题总数": record.total_issues,
            "严重问题": record.critical_count,
            "警告问题": record.warning_count,
            "提示问题": record.info_count,
            "涉及店铺": ", ".join(record.stores),
            "涉及类目": ", ".join(record.categories),
        })

    df = pd.DataFrame(data)
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="检查历史")
        marker_df = pd.DataFrame({"marker": ["ecommerce_checker_tool_generated"]})
        marker_df.to_excel(writer, index=False, sheet_name=TOOL_MARKER_SHEET)
    return output_path
