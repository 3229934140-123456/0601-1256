from __future__ import annotations

import os
from typing import Dict, List, Optional, Set

from .config import CATEGORY_RULES
from .config_loader import CheckerConfig
from .models import CheckIssue, CheckResult, Product
from .utils import validate_sku

try:
    from PIL import Image as PILImage
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False


class ProductChecker:
    def __init__(self, products: List[Product], base_dir: str = "", config: Optional[CheckerConfig] = None):
        self.products = products
        self.base_dir = base_dir
        self.config = config
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

        title_max_length = self.config.get("title_max_length", product.shop) if self.config else 60
        sensitive_words = self.config.get("sensitive_words", product.shop) if self.config else []

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

        if len(title) > title_max_length:
            issues.append(
                CheckIssue(
                    sku=product.sku,
                    field="title",
                    issue_type="title_too_long",
                    message=f"标题长度为 {len(title)} 字符，超过最大限制 {title_max_length} 字符",
                    level="warning",
                    suggestion=f"请精简标题至 {title_max_length} 字符以内",
                    auto_fixable=True,
                    fixed_value=title[:title_max_length],
                )
            )

        found_sensitive = [word for word in sensitive_words if word in title]
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
                    fixed_value=self._remove_sensitive_words(title, sensitive_words),
                )
            )

        return issues

    def _remove_sensitive_words(self, title: str, sensitive_words: List[str]) -> str:
        result = title
        for word in sensitive_words:
            result = result.replace(word, "")
        return result

    def _check_price(self, product: Product) -> List[CheckIssue]:
        issues = []
        price = product.price

        price_min = self.config.get("price_min", product.shop) if self.config else 0.1
        price_max = self.config.get("price_max", product.shop) if self.config else 999999

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

        if price < price_min or price > price_max:
            issues.append(
                CheckIssue(
                    sku=product.sku,
                    field="price",
                    issue_type="price_out_of_range",
                    message=f"价格 {price} 超出合理区间 [{price_min}, {price_max}]",
                    level="warning",
                    suggestion=f"请确认价格是否在 {price_min} - {price_max} 范围内",
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
        shop = product.shop

        detail_images_min_count = self.config.get("detail_images_min_count", shop) if self.config else 3
        image_min_width = self.config.get("image_min_width", shop) if self.config else 800
        image_min_height = self.config.get("image_min_height", shop) if self.config else 800
        image_max_size_mb = self.config.get("image_max_size_mb", shop) if self.config else 5.0

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
        else:
            issues.extend(self._check_single_image(product.main_image, "主图", image_min_width, image_min_height, image_max_size_mb))

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
        else:
            for idx, img_path in enumerate(product.detail_images):
                issues.extend(self._check_single_image(img_path, f"详情图{idx+1}", image_min_width, image_min_height, image_max_size_mb))

            if len(product.detail_images) < detail_images_min_count:
                issues.append(
                    CheckIssue(
                        sku=product.sku,
                        field="detail_images",
                        issue_type="insufficient_detail_images",
                        message=f"详情图数量不足，当前 {len(product.detail_images)} 张，建议至少 {detail_images_min_count} 张",
                        level="info",
                        suggestion="请补充更多详情图以展示商品细节",
                    )
                )

        return issues

    def _is_url(self, path: str) -> bool:
        return path.startswith("http://") or path.startswith("https://")

    def _check_single_image(self, image_path: str, image_label: str, min_width: int, min_height: int, max_size_mb: float) -> List[CheckIssue]:
        issues = []

        if self._is_url(image_path):
            return issues

        resolved_path = image_path
        if self.base_dir and not os.path.isabs(resolved_path):
            resolved_path = os.path.join(self.base_dir, resolved_path)
            resolved_path = os.path.normpath(resolved_path)

        if not os.path.isfile(resolved_path):
            issues.append(
                CheckIssue(
                    sku="",
                    field=image_label,
                    issue_type="image_not_found",
                    message=f"{image_label}文件不存在: {image_path}",
                    level="warning",
                    suggestion="请检查图片路径是否正确，确保图片文件存在",
                )
            )
            return issues

        try:
            file_size = os.path.getsize(resolved_path)
            file_size_mb = file_size / (1024 * 1024)
            if file_size_mb > max_size_mb:
                issues.append(
                    CheckIssue(
                        sku="",
                        field=image_label,
                        issue_type="image_too_large",
                        message=f"{image_label}文件过大: {file_size_mb:.2f}MB，超过限制 {max_size_mb}MB",
                        level="warning",
                        suggestion="请压缩图片大小以提高页面加载速度",
                    )
                )
        except Exception:
            pass

        if not _PIL_AVAILABLE:
            return issues

        try:
            with PILImage.open(resolved_path) as img:
                img.verify()
        except Exception as e:
            issues.append(
                CheckIssue(
                    sku="",
                    field=image_label,
                    issue_type="image_corrupted",
                    message=f"{image_label}文件损坏无法打开: {str(e)}",
                    level="critical",
                    suggestion="请重新上传或修复该图片",
                )
            )
            return issues

        try:
            with PILImage.open(resolved_path) as img:
                width, height = img.size
                if width < min_width or height < min_height:
                    issues.append(
                        CheckIssue(
                            sku="",
                            field=image_label,
                            issue_type="image_too_small",
                            message=f"{image_label}尺寸过小: {width}x{height}，建议不小于 {min_width}x{min_height}",
                            level="warning",
                            suggestion="请使用更高分辨率的图片以保证展示效果",
                        )
                    )
        except Exception:
            pass

        return issues

    def _check_category(self, product: Product) -> List[CheckIssue]:
        issues = []
        category = product.category
        title = product.title

        category_rules = self.config.get("category_rules", product.shop) if self.config else CATEGORY_RULES

        if not category:
            suggested_category = self._suggest_category(title, category_rules)
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

    def _suggest_category(self, title: str, category_rules: Dict[str, List[str]]) -> Optional[str]:
        if not title:
            return None

        for category, keywords in category_rules.items():
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
