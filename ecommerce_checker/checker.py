from __future__ import annotations

from typing import Dict, List, Optional, Set

from .config import (
    CATEGORY_RULES,
    PRICE_MAX,
    PRICE_MIN,
    SENSITIVE_WORDS,
    TITLE_MAX_LENGTH,
)
from .models import CheckIssue, CheckResult, Product
from .utils import validate_sku


class ProductChecker:
    def __init__(self, products: List[Product]):
        self.products = products
        self._sku_set: Set[str] = set()
        self._sku_counts: Dict[str, int] = {}
        self._init_sku_tracking()

    def _init_sku_tracking(self) -> None:
        for product in self.products:
            sku = product.sku
            self._sku_counts[sku] = self._sku_counts.get(sku, 0) + 1
            self._sku_set.add(sku)

    def check_all(self, store_filter: Optional[str] = None) -> List[CheckResult]:
        results = []
        for product in self.products:
            if store_filter and product.shop != store_filter:
                continue
            result = self.check_product(product)
            results.append(result)
        return results

    def check_product(self, product: Product) -> CheckResult:
        result = CheckResult(product=product)

        result.issues.extend(self._check_sku(product))
        result.issues.extend(self._check_title(product))
        result.issues.extend(self._check_price(product))
        result.issues.extend(self._check_stock(product))
        result.issues.extend(self._check_images(product))
        result.issues.extend(self._check_category(product))
        result.issues.extend(self._check_duplicate_sku(product))

        return result

    def _check_sku(self, product: Product) -> List[CheckIssue]:
        issues = []
        sku = product.sku

        if not sku:
            issues.append(
                CheckIssue(
                    sku=product.sku or "UNKNOWN",
                    field="sku",
                    issue_type="missing_sku",
                    message="商品编码为空",
                    level="critical",
                    suggestion="请填写有效的商品编码",
                )
            )
            return issues

        if not validate_sku(sku):
            issues.append(
                CheckIssue(
                    sku=sku,
                    field="sku",
                    issue_type="invalid_sku_format",
                    message=f"商品编码格式不正确，应为6-20位字母数字组合: {sku}",
                    level="warning",
                    suggestion="请修改为符合规范的商品编码",
                )
            )

        return issues

    def _check_title(self, product: Product) -> List[CheckIssue]:
        issues = []
        title = product.title

        if not title:
            issues.append(
                CheckIssue(
                    sku=product.sku,
                    field="title",
                    issue_type="missing_title",
                    message="商品标题为空",
                    level="critical",
                    suggestion="请填写商品标题",
                )
            )
            return issues

        if len(title) > TITLE_MAX_LENGTH:
            issues.append(
                CheckIssue(
                    sku=product.sku,
                    field="title",
                    issue_type="title_too_long",
                    message=f"标题长度为 {len(title)} 字符，超过最大限制 {TITLE_MAX_LENGTH} 字符",
                    level="warning",
                    suggestion=f"请精简标题至 {TITLE_MAX_LENGTH} 字符以内",
                    auto_fixable=True,
                    fixed_value=title[:TITLE_MAX_LENGTH],
                )
            )

        found_sensitive = [word for word in SENSITIVE_WORDS if word in title]
        if found_sensitive:
            issues.append(
                CheckIssue(
                    sku=product.sku,
                    field="title",
                    issue_type="sensitive_words",
                    message=f"标题包含敏感词: {', '.join(found_sensitive)}",
                    level="warning",
                    suggestion="请删除或替换敏感词",
                    auto_fixable=True,
                    fixed_value=self._remove_sensitive_words(title),
                )
            )

        return issues

    def _remove_sensitive_words(self, title: str) -> str:
        result = title
        for word in SENSITIVE_WORDS:
            result = result.replace(word, "")
        return result

    def _check_price(self, product: Product) -> List[CheckIssue]:
        issues = []
        price = product.price

        if price is None:
            issues.append(
                CheckIssue(
                    sku=product.sku,
                    field="price",
                    issue_type="missing_price",
                    message="商品价格为空或格式不正确",
                    level="critical",
                    suggestion="请填写有效的商品价格",
                )
            )
            return issues

        if price < PRICE_MIN or price > PRICE_MAX:
            issues.append(
                CheckIssue(
                    sku=product.sku,
                    field="price",
                    issue_type="price_out_of_range",
                    message=f"价格 {price} 超出合理区间 [{PRICE_MIN}, {PRICE_MAX}]",
                    level="warning",
                    suggestion=f"请确认价格是否在 {PRICE_MIN} - {PRICE_MAX} 范围内",
                )
            )

        return issues

    def _check_stock(self, product: Product) -> List[CheckIssue]:
        issues = []
        stock = product.stock

        if stock is None:
            issues.append(
                CheckIssue(
                    sku=product.sku,
                    field="stock",
                    issue_type="missing_stock",
                    message="商品库存为空或格式不正确",
                    level="critical",
                    suggestion="请填写有效的库存数量",
                )
            )
            return issues

        if stock < 0:
            issues.append(
                CheckIssue(
                    sku=product.sku,
                    field="stock",
                    issue_type="negative_stock",
                    message=f"库存数量为负数: {stock}",
                    level="critical",
                    suggestion="请填写非负的库存数量",
                )
            )

        if stock == 0:
            issues.append(
                CheckIssue(
                    sku=product.sku,
                    field="stock",
                    issue_type="zero_stock",
                    message="商品库存为0",
                    level="info",
                    suggestion="请确认是否需要补充库存",
                )
            )

        return issues

    def _check_images(self, product: Product) -> List[CheckIssue]:
        issues = []

        if not product.main_image:
            issues.append(
                CheckIssue(
                    sku=product.sku,
                    field="main_image",
                    issue_type="missing_main_image",
                    message="缺少商品主图",
                    level="critical",
                    suggestion=f"请在 images 目录下添加 {product.sku}_main.jpg 或 {product.sku}.jpg 作为主图",
                )
            )

        if not product.detail_images:
            issues.append(
                CheckIssue(
                    sku=product.sku,
                    field="detail_images",
                    issue_type="missing_detail_images",
                    message="缺少商品详情图",
                    level="warning",
                    suggestion=f"请在 images 目录下添加 {product.sku}_detail_1.jpg, {product.sku}_detail_2.jpg 等详情图",
                )
            )
        elif len(product.detail_images) < 3:
            issues.append(
                CheckIssue(
                    sku=product.sku,
                    field="detail_images",
                    issue_type="insufficient_detail_images",
                    message=f"详情图数量不足，当前 {len(product.detail_images)} 张，建议至少3张",
                    level="info",
                    suggestion="请补充更多详情图以展示商品细节",
                )
            )

        return issues

    def _check_category(self, product: Product) -> List[CheckIssue]:
        issues = []
        category = product.category
        title = product.title

        if not category:
            suggested_category = self._suggest_category(title)
            issues.append(
                CheckIssue(
                    sku=product.sku,
                    field="category",
                    issue_type="missing_category",
                    message="商品类目为空",
                    level="warning",
                    suggestion=f"建议类目: {suggested_category}" if suggested_category else "请填写商品类目",
                    auto_fixable=suggested_category is not None,
                    fixed_value=suggested_category,
                )
            )

        return issues

    def _suggest_category(self, title: str) -> Optional[str]:
        if not title:
            return None

        for category, keywords in CATEGORY_RULES.items():
            for keyword in keywords:
                if keyword in title:
                    return category

        return None

    def _check_duplicate_sku(self, product: Product) -> List[CheckIssue]:
        issues = []
        sku = product.sku

        if self._sku_counts.get(sku, 0) > 1:
            issues.append(
                CheckIssue(
                    sku=sku,
                    field="sku",
                    issue_type="duplicate_sku",
                    message=f"商品编码重复，共出现 {self._sku_counts[sku]} 次",
                    level="critical",
                    suggestion="请修改重复的商品编码，确保唯一性",
                )
            )

        return issues

    def get_issue_summary(self, results: List[CheckResult]) -> Dict[str, Dict[str, int]]:
        summary = {}
        for result in results:
            for issue in result.issues:
                level = issue.level
                issue_type = issue.issue_type
                if level not in summary:
                    summary[level] = {}
                summary[level][issue_type] = summary[level].get(issue_type, 0) + 1
        return summary
