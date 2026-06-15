from __future__ import annotations

import os
from typing import Dict, List, Optional, Tuple

import pandas as pd

from .models import CheckResult, FixPreview, Product


class ProductFixer:
    def __init__(self, products: List[Product]):
        self.products = products
        self._product_map: Dict[str, Product] = {p.sku: p for p in products}

    def preview_fixes(self, check_results: List[CheckResult]) -> List[FixPreview]:
        previews = []
        for result in check_results:
            for issue in result.issues:
                if issue.auto_fixable and issue.fixed_value is not None:
                    product = self._product_map.get(issue.sku)
                    if product:
                        old_value = getattr(product, issue.field, None)
                        previews.append(
                            FixPreview(
                                sku=issue.sku,
                                field=issue.field,
                                old_value=old_value,
                                new_value=issue.fixed_value,
                                reason=issue.message,
                            )
                        )
        return previews

    def apply_fixes(self, check_results: List[CheckResult], preview: bool = False) -> Tuple[List[FixPreview], List[FixPreview]]:
        applied: List[FixPreview] = []
        skipped: List[FixPreview] = []

        previews = self.preview_fixes(check_results)

        if preview:
            return previews, []

        for fix in previews:
            product = self._product_map.get(fix.sku)
            if product:
                old_value = getattr(product, fix.field, None)
                setattr(product, fix.field, fix.new_value)
                applied.append(fix)

        return applied, skipped

    def save_fixes(self, output_dir: str) -> List[str]:
        saved_files = []
        file_groups: Dict[str, List[Product]] = {}

        for product in self.products:
            source_file = product.source_file
            if source_file not in file_groups:
                file_groups[source_file] = []
            file_groups[source_file].append(product)

        os.makedirs(output_dir, exist_ok=True)

        for source_file, products in file_groups.items():
            base_name = os.path.splitext(os.path.basename(source_file))[0]
            output_file = os.path.join(output_dir, f"{base_name}_fixed.xlsx")

            data = []
            for p in products:
                data.append({
                    "商品编码": p.sku,
                    "标题": p.title,
                    "价格": p.price,
                    "库存": p.stock,
                    "类目": p.category,
                    "店铺": p.shop,
                    "主图": p.main_image,
                    "详情图": ";".join(p.detail_images),
                    "来源文件": p.source_file,
                })

            df = pd.DataFrame(data)
            df.to_excel(output_file, index=False)
            saved_files.append(output_file)

        return saved_files

    def generate_fix_list(self, check_results: List[CheckResult]) -> List[Dict]:
        fix_list = []
        for result in check_results:
            if not result.passed:
                item = {
                    "sku": result.product.sku,
                    "title": result.product.title,
                    "shop": result.product.shop,
                    "issues": [],
                }
                for issue in result.issues:
                    item["issues"].append({
                        "field": issue.field,
                        "issue_type": issue.issue_type,
                        "message": issue.message,
                        "level": issue.level,
                        "suggestion": issue.suggestion,
                        "auto_fixable": issue.auto_fixable,
                    })
                fix_list.append(item)
        return fix_list
