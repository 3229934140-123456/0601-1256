import os
import glob
from typing import Dict, List, Optional, Tuple

import pandas as pd

from .config import IMAGE_EXTENSIONS
from .models import Product, ScanResult
from .utils import clean_text, parse_price, parse_stock


class ProductReader:
    SUPPORTED_EXTENSIONS = (".xlsx", ".xls", ".csv")

    EXCLUDED_FILENAMES = [
        "fix_list",
        "fix_preview",
        "check_report",
        "_fixed",
    ]

    EXCLUDED_DIRNAMES = [
        "fixed_data",
        "check_report_data",
        "__pycache__",
        ".git",
    ]

    COLUMN_MAPPINGS = {
        "sku": ["sku", "商品编码", "商品编号", "货号", "编码", "product_id", "productid"],
        "title": ["title", "标题", "商品名称", "商品标题", "名称", "product_name", "productname", "name"],
        "price": ["price", "价格", "售价", "单价", "商品价格", "sale_price", "saleprice"],
        "stock": ["stock", "库存", "数量", "库存数量", "inventory", "quantity", "qty"],
        "category": ["category", "类目", "分类", "商品分类", "商品类目", "品类"],
        "shop": ["shop", "店铺", "商店", "门店", "store"],
        "main_image": ["main_image", "主图", "主图链接", "主图地址"],
        "detail_image": ["detail_image", "详情图", "详情图链接", "详情图地址"],
    }

    def __init__(self, folder_path: str):
        self.folder_path = folder_path
        self._products: List[Product] = []

    def _is_excluded_file(self, filename: str) -> bool:
        basename = os.path.basename(filename).lower()
        for keyword in self.EXCLUDED_FILENAMES:
            if keyword in basename:
                return True
        return False

    def _is_in_excluded_dir(self, filepath: str) -> bool:
        rel_path = os.path.relpath(filepath, self.folder_path)
        path_parts = rel_path.split(os.sep)
        for part in path_parts:
            if part.lower() in [d.lower() for d in self.EXCLUDED_DIRNAMES]:
                return True
        return False

    def scan_files(self) -> List[str]:
        files = []
        for ext in self.SUPPORTED_EXTENSIONS:
            pattern = os.path.join(self.folder_path, "**", f"*{ext}")
            all_files = glob.glob(pattern, recursive=True)
            for f in all_files:
                if not self._is_excluded_file(f) and not self._is_in_excluded_dir(f):
                    files.append(f)
        return sorted(files)

    def _map_columns(self, df: pd.DataFrame) -> Dict[str, str]:
        mapping = {}
        df_columns = {str(col).lower(): col for col in df.columns}

        for standard_name, candidates in self.COLUMN_MAPPINGS.items():
            for candidate in candidates:
                candidate_lower = candidate.lower()
                if candidate_lower in df_columns:
                    mapping[standard_name] = df_columns[candidate_lower]
                    break
                for df_col in df_columns:
                    if candidate_lower in df_col or df_col in candidate_lower:
                        mapping[standard_name] = df_columns[df_col]
                        break
                if standard_name in mapping:
                    break

        return mapping

    def _find_images_for_sku(self, sku: str, base_dir: str) -> Tuple[Optional[str], List[str]]:
        images_dir = os.path.join(base_dir, "images")
        if not os.path.isdir(images_dir):
            return None, []

        main_image = None
        detail_images: List[str] = []

        for ext in IMAGE_EXTENSIONS:
            main_patterns = [
                os.path.join(images_dir, f"{sku}_main{ext}"),
                os.path.join(images_dir, f"{sku}{ext}"),
            ]
            for pattern in main_patterns:
                matches = glob.glob(pattern)
                if matches and main_image is None:
                    main_image = matches[0]
                    break

            detail_pattern = os.path.join(images_dir, f"{sku}_detail_*{ext}")
            detail_images.extend(glob.glob(detail_pattern))

        detail_images.sort()
        return main_image, detail_images

    def _read_file(self, file_path: str) -> List[Product]:
        products = []
        try:
            if file_path.endswith(".csv"):
                df = pd.read_csv(file_path, dtype=str)
            else:
                df = pd.read_excel(file_path, dtype=str)

            df = df.dropna(how="all")
            if df.empty:
                return products

            col_map = self._map_columns(df)

            if "sku" not in col_map:
                return products

            base_dir = os.path.dirname(file_path)

            for _, row in df.iterrows():
                sku_raw = row.get(col_map["sku"], "")
                if pd.isna(sku_raw) or not str(sku_raw).strip():
                    continue

                sku = clean_text(str(sku_raw))
                if not sku:
                    continue

                product = Product(sku=sku, source_file=file_path)

                if "title" in col_map:
                    title_val = row.get(col_map["title"], "")
                    if not pd.isna(title_val):
                        product.title = clean_text(str(title_val))

                if "price" in col_map:
                    price_val = row.get(col_map["price"], "")
                    if not pd.isna(price_val):
                        product.price = parse_price(str(price_val))

                if "stock" in col_map:
                    stock_val = row.get(col_map["stock"], "")
                    if not pd.isna(stock_val):
                        product.stock = parse_stock(str(stock_val))

                if "category" in col_map:
                    category_val = row.get(col_map["category"], "")
                    if not pd.isna(category_val):
                        product.category = clean_text(str(category_val))

                if "shop" in col_map:
                    shop_val = row.get(col_map["shop"], "")
                    if not pd.isna(shop_val):
                        product.shop = clean_text(str(shop_val))

                table_main_image = None
                table_detail_images: List[str] = []

                if "main_image" in col_map:
                    main_img_val = row.get(col_map["main_image"], "")
                    if not pd.isna(main_img_val) and str(main_img_val).strip():
                        table_main_image = str(main_img_val).strip()

                if "detail_image" in col_map:
                    detail_img_val = row.get(col_map["detail_image"], "")
                    if not pd.isna(detail_img_val) and str(detail_img_val).strip():
                        detail_str = str(detail_img_val).strip()
                        for separator in [";", ",", "\n", "|"]:
                            if separator in detail_str:
                                table_detail_images = [p.strip() for p in detail_str.split(separator) if p.strip()]
                                break
                        if not table_detail_images and detail_str:
                            table_detail_images = [detail_str]

                if table_main_image or table_detail_images:
                    product.main_image = table_main_image
                    product.detail_images = table_detail_images
                else:
                    main_image, detail_images = self._find_images_for_sku(sku, base_dir)
                    product.main_image = main_image
                    product.detail_images = detail_images

                products.append(product)

        except Exception as e:
            raise RuntimeError(f"读取文件 {file_path} 失败: {e}")

        return products

    def read_products(self) -> ScanResult:
        result = ScanResult()
        files = self.scan_files()
        result.total_files = len(files)

        self._products = []
        stores_set = set()
        categories_set = set()

        for file_path in files:
            try:
                file_products = self._read_file(file_path)
                self._products.extend(file_products)
                for p in file_products:
                    if p.shop:
                        stores_set.add(p.shop)
                    if p.category:
                        categories_set.add(p.category)
            except RuntimeError as e:
                result.errors.append(str(e))

        result.products = self._products
        result.total_products = len(self._products)
        result.stores = sorted(stores_set)
        result.categories = sorted(categories_set)

        return result

    def get_sku_list(self) -> List[str]:
        return [product.sku for product in self._products]
