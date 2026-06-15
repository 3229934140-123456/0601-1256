from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd

from .config import ERROR_LEVELS
from .models import CheckResult, FixPreview, ScanResult


class ReportGenerator:
    def __init__(self, scan_result: ScanResult, check_results: List[CheckResult]):
        self.scan_result = scan_result
        self.check_results = check_results

    def generate_console_report(self, level_filter: Optional[str] = None) -> str:
        lines = []
        lines.append("=" * 80)
        lines.append("电商商品上架资料检查报告")
        lines.append("=" * 80)
        lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        lines.append("一、扫描概览")
        lines.append("-" * 40)
        lines.append(f"扫描文件数: {self.scan_result.total_files}")
        lines.append(f"商品总数: {self.scan_result.total_products}")
        lines.append(f"涉及店铺: {', '.join(self.scan_result.stores) if self.scan_result.stores else '无'}")
        lines.append(f"涉及类目: {', '.join(self.scan_result.categories) if self.scan_result.categories else '无'}")
        lines.append("")

        total_issues = sum(len(r.issues) for r in self.check_results)
        passed_count = sum(1 for r in self.check_results if r.passed)
        failed_count = len(self.check_results) - passed_count

        lines.append("二、检查概览")
        lines.append("-" * 40)
        lines.append(f"检查商品数: {len(self.check_results)}")
        lines.append(f"通过检查: {passed_count}")
        lines.append(f"存在问题: {failed_count}")
        lines.append(f"问题总数: {total_issues}")
        lines.append("")

        level_stats = self._get_level_stats(level_filter)
        lines.append("三、问题分级统计")
        lines.append("-" * 40)
        for level, count in level_stats.items():
            level_name = ERROR_LEVELS.get(level, level)
            lines.append(f"  {level_name}: {count} 个")
        lines.append("")

        issue_type_stats = self._get_issue_type_stats(level_filter)
        if issue_type_stats:
            lines.append("四、问题类型统计")
            lines.append("-" * 40)
            for issue_type, count in sorted(issue_type_stats.items(), key=lambda x: -x[1]):
                lines.append(f"  {issue_type}: {count} 个")
            lines.append("")

        lines.append("五、问题详情")
        lines.append("-" * 40)
        for result in self.check_results:
            if result.passed:
                continue
            lines.append(f"\n商品: {result.product.sku} - {result.product.title}")
            lines.append(f"店铺: {result.product.shop}")
            for issue in result.issues:
                if level_filter and issue.level != level_filter:
                    continue
                level_name = ERROR_LEVELS.get(issue.level, issue.level)
                lines.append(f"  [{level_name}] {issue.field}: {issue.message}")
                if issue.suggestion:
                    lines.append(f"    建议: {issue.suggestion}")
                if issue.auto_fixable:
                    lines.append(f"    可自动修复")

        lines.append("")
        lines.append("=" * 80)
        return "\n".join(lines)

    def _get_level_stats(self, level_filter: Optional[str] = None) -> Dict[str, int]:
        stats: Dict[str, int] = {}
        for result in self.check_results:
            for issue in result.issues:
                if level_filter and issue.level != level_filter:
                    continue
                stats[issue.level] = stats.get(issue.level, 0) + 1
        return stats

    def _get_issue_type_stats(self, level_filter: Optional[str] = None) -> Dict[str, int]:
        stats: Dict[str, int] = {}
        for result in self.check_results:
            for issue in result.issues:
                if level_filter and issue.level != level_filter:
                    continue
                stats[issue.issue_type] = stats.get(issue.issue_type, 0) + 1
        return stats

    def export_excel(self, output_path: str, level_filter: Optional[str] = None) -> str:
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)

        data = []
        for result in self.check_results:
            for issue in result.issues:
                if level_filter and issue.level != level_filter:
                    continue
                data.append({
                    "商品编码": result.product.sku,
                    "商品标题": result.product.title,
                    "店铺": result.product.shop,
                    "问题字段": issue.field,
                    "问题类型": issue.issue_type,
                    "问题描述": issue.message,
                    "错误级别": ERROR_LEVELS.get(issue.level, issue.level),
                    "修复建议": issue.suggestion,
                    "可自动修复": "是" if issue.auto_fixable else "否",
                    "来源文件": result.product.source_file,
                })

        df = pd.DataFrame(data)
        df.to_excel(output_path, index=False)
        return output_path

    def export_json(self, output_path: str, level_filter: Optional[str] = None) -> str:
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)

        report_data = {
            "generated_at": datetime.now().isoformat(),
            "scan_summary": {
                "total_files": self.scan_result.total_files,
                "total_products": self.scan_result.total_products,
                "stores": self.scan_result.stores,
                "categories": self.scan_result.categories,
            },
            "check_summary": {
                "total_checked": len(self.check_results),
                "passed": sum(1 for r in self.check_results if r.passed),
                "failed": sum(1 for r in self.check_results if not r.passed),
                "total_issues": sum(len(r.issues) for r in self.check_results),
            },
            "level_stats": self._get_level_stats(level_filter),
            "issue_type_stats": self._get_issue_type_stats(level_filter),
            "issues": [],
        }

        for result in self.check_results:
            for issue in result.issues:
                if level_filter and issue.level != level_filter:
                    continue
                report_data["issues"].append({
                    "sku": result.product.sku,
                    "title": result.product.title,
                    "shop": result.product.shop,
                    "field": issue.field,
                    "issue_type": issue.issue_type,
                    "message": issue.message,
                    "level": issue.level,
                    "level_name": ERROR_LEVELS.get(issue.level, issue.level),
                    "suggestion": issue.suggestion,
                    "auto_fixable": issue.auto_fixable,
                    "fixed_value": issue.fixed_value,
                    "source_file": result.product.source_file,
                })

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        return output_path

    def export_fix_list(self, output_path: str, level_filter: Optional[str] = None) -> str:
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)

        data = []
        for result in self.check_results:
            if result.passed:
                continue
            product_issues = [i for i in result.issues if (not level_filter or i.level == level_filter)]
            if not product_issues:
                continue
            data.append({
                "商品编码": result.product.sku,
                "商品标题": result.product.title,
                "店铺": result.product.shop,
                "问题数量": len(product_issues),
                "待修改内容": "\n".join([f"- {i.field}: {i.message}" for i in product_issues]),
                "修复建议": "\n".join([f"- {i.suggestion}" for i in product_issues if i.suggestion]),
            })

        df = pd.DataFrame(data)
        df.to_excel(output_path, index=False)
        return output_path

    def export_fix_preview(self, previews: List[FixPreview], output_path: str) -> str:
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)

        data = []
        for preview in previews:
            data.append({
                "商品编码": preview.sku,
                "修改字段": preview.field,
                "原值": str(preview.old_value),
                "新值": str(preview.new_value),
                "修改原因": preview.reason,
            })

        df = pd.DataFrame(data)
        df.to_excel(output_path, index=False)
        return output_path
