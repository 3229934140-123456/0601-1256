import os
import struct
from openpyxl import Workbook
from PIL import Image, ImageDraw, ImageFont


def create_corrupted_image(filepath: str) -> None:
    with open(filepath, "wb") as f:
        f.write(b"\xff\xd8\xff\xe0\x00\x10JFIF")
        f.write(b"\x00" * 100)


def create_large_image(filepath: str, size_mb: float) -> None:
    pixels = int((size_mb * 1024 * 1024) / 3) + 1
    width = int(pixels**0.5) + 1
    height = int(pixels / width) + 1
    img = Image.new("RGB", (width, height), (255, 0, 0))
    img.save(filepath, "JPEG", quality=100)


def create_sample_data():
    base_dir = os.path.join(os.path.dirname(__file__), "sample_data")
    images_dir = os.path.join(base_dir, "images")
    fixed_dir = os.path.join(base_dir, "fixed_data")

    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(fixed_dir, exist_ok=True)

    wb = Workbook()
    ws = wb.active
    ws.title = "商品数据"

    headers = ["商品编码(SKU)", "标题", "价格", "库存", "类目", "店铺", "主图", "详情图"]
    ws.append(headers)

    data = [
        ["PROD001", "无线蓝牙耳机 高音质降噪运动耳机", 199.00, 100, "数码配件", "旗舰店",
         "images/PROD001_main.jpg",
         "images/PROD001_detail_1.jpg;images/PROD001_detail_2.jpg;images/PROD001_detail_3.jpg"],
        ["PROD002", "这是一个超长标题" * 20, 99.99, 50, "家居用品", "专营店",
         "https://cdn.example.com/images/PROD002.jpg",
         "https://cdn.example.com/images/PROD002_detail_1.jpg;https://cdn.example.com/images/PROD002_detail_2.jpg"],
        ["PROD003", "高仿奢侈品包包 原单复刻爆款", 999.00, 20, "箱包配饰", "旗舰店", "", ""],
        ["PROD004", "", 50.00, 0, "服装", "专营店", "", ""],
        ["PROD005", "纯棉T恤 夏季新款短袖", -10.00, -5, "", "旗舰店", "", ""],
        ["PROD006", "运动鞋 轻便透气跑步鞋", 299.00, -100, "鞋靴", "旗舰店",
         "images/PROD001_main.jpg",
         "images/PROD001_detail_1.jpg"],
        ["PROD007", "纯棉衬衫 商务休闲长袖", 159.00, 30, "服装", "旗舰店",
         "https://cdn.example.com/images/PROD007.jpg", ""],
        ["PROD008", "小尺寸图片测试商品", 89.00, 50, "家居用品", "专营店",
         "images/PROD008_main.jpg",
         "images/PROD008_detail_1.jpg"],
        ["PROD009", "损坏图片测试商品", 199.00, 50, "数码配件", "专营店",
         "images/PROD009_main.jpg",
         ""],
        ["PROD010", "大文件图片测试商品", 299.00, 50, "箱包配饰", "专营店",
         "images/PROD010_main.jpg",
         ""],
    ]

    for row in data:
        ws.append(row)

    excel_path = os.path.join(base_dir, "products.xlsx")
    wb.save(excel_path)
    print(f"商品数据已创建: {excel_path}")

    def create_image(filename, color, text, size=(400, 400)):
        img = Image.new("RGB", size, color)
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", 30)
        except:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (size[0] - text_width) // 2
        y = (size[1] - text_height) // 2
        draw.text((x, y), text, fill="white", font=font)

        img_path = os.path.join(images_dir, filename)
        img.save(img_path, "JPEG")
        print(f"图片已创建: {img_path}")

    images_to_create = [
        ("PROD001_main.jpg", (66, 133, 244), "PROD001 主图", (800, 800)),
        ("PROD001_detail_1.jpg", (234, 67, 53), "PROD001 详情1", (800, 800)),
        ("PROD001_detail_2.jpg", (251, 188, 5), "PROD001 详情2", (800, 800)),
        ("PROD001_detail_3.jpg", (52, 168, 83), "PROD001 详情3", (800, 800)),
        ("PROD002.jpg", (156, 39, 176), "PROD002 主图", (800, 800)),
        ("PROD002_detail_1.jpg", (0, 188, 212), "PROD002 详情1", (800, 800)),
        ("PROD007_detail_1.jpg", (255, 87, 34), "PROD007 详情1", (800, 800)),
        ("PROD007_detail_2.jpg", (63, 81, 181), "PROD007 详情2", (800, 800)),
        ("PROD007_detail_3.jpg", (0, 150, 136), "PROD007 详情3", (800, 800)),
        ("PROD008_main.jpg", (128, 128, 128), "PROD008 小尺寸主图", (400, 400)),
        ("PROD008_detail_1.jpg", (192, 192, 192), "PROD008 小尺寸详情", (600, 600)),
    ]

    for filename, color, text, size in images_to_create:
        create_image(filename, color, text, size)

    corrupted_path = os.path.join(images_dir, "PROD009_main.jpg")
    create_corrupted_image(corrupted_path)
    print(f"损坏图片已创建: {corrupted_path}")

    large_path = os.path.join(images_dir, "PROD010_main.jpg")
    create_large_image(large_path, 6.0)
    print(f"大文件图片已创建: {large_path}")

    wb_fake = Workbook()
    ws_fake = wb_fake.active
    ws_fake.append(["SKU", "标题", "错误信息"])
    ws_fake.append(["TEST001", "假数据", "这是模拟报告文件，不应被读取"])

    fake_fixed = os.path.join(fixed_dir, "products_fixed.xlsx")
    wb_fake.save(fake_fixed)
    print(f"模拟修复后文件(应被排除): {fake_fixed}")

    fake_fix_list = os.path.join(fixed_dir, "fix_list.xlsx")
    wb_fake.save(fake_fix_list)
    print(f"模拟待修改清单(应被排除): {fake_fix_list}")

    fake_fix_preview = os.path.join(fixed_dir, "fix_preview.xlsx")
    wb_fake.save(fake_fix_preview)
    print(f"模拟修复预览(应被排除): {fake_fix_preview}")

    fake_report = os.path.join(base_dir, "check_report_20240615.xlsx")
    wb_fake.save(fake_report)
    print(f"模拟检查报告(应被排除): {fake_report}")

    config_content = """# 电商商品检查配置文件
# 全局配置（所有店铺通用）
global:
  title_max_length: 60
  price_min: 0.1
  price_max: 999999
  detail_images_min_count: 3
  image_min_width: 800
  image_min_height: 800
  image_max_size_mb: 5.0
  sensitive_words:
    - 最
    - 第一
    - 绝对
    - 国家级
    - 最高级
    - 全网最低
    - 秒杀
    - 爆款
    - 限量
    - 独家

# 店铺级配置（覆盖全局）
shops:
  旗舰店:
    title_max_length: 80
    sensitive_words:
      - 官方禁用词1
      - 官方禁用词2

  专营店:
    title_max_length: 50
    price_min: 1.0
    price_max: 99999
    detail_images_min_count: 5
    image_min_width: 1000
    image_min_height: 1000
"""
    config_path = os.path.join(base_dir, "checker_config.yaml")
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(config_content)
    print(f"示例配置文件已创建: {config_path}")

    print("\n所有示例数据创建完成！")


if __name__ == "__main__":
    create_sample_data()
