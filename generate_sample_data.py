import os
from openpyxl import Workbook
from PIL import Image, ImageDraw, ImageFont


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
        ["PROD005", "纯棉T恤 夏季新款短袖", -10.00, -5, "", "旗舰店",
         "", ""],
        ["PROD006", "运动鞋 轻便透气跑步鞋", 299.00, -100, "鞋靴", "旗舰店",
         "images/PROD001_main.jpg",
         "images/PROD001_detail_1.jpg"],
    ]

    for row in data:
        ws.append(row)

    excel_path = os.path.join(base_dir, "products.xlsx")
    wb.save(excel_path)
    print(f"商品数据已创建: {excel_path}")

    def create_image(filename, color, text):
        img = Image.new("RGB", (400, 400), color)
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", 30)
        except:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (400 - text_width) // 2
        y = (400 - text_height) // 2
        draw.text((x, y), text, fill="white", font=font)

        img_path = os.path.join(images_dir, filename)
        img.save(img_path, "JPEG")
        print(f"图片已创建: {img_path}")

    images_to_create = [
        ("PROD001_main.jpg", (66, 133, 244), "PROD001 主图"),
        ("PROD001_detail_1.jpg", (234, 67, 53), "PROD001 详情1"),
        ("PROD001_detail_2.jpg", (251, 188, 5), "PROD001 详情2"),
        ("PROD001_detail_3.jpg", (52, 168, 83), "PROD001 详情3"),
        ("PROD002.jpg", (156, 39, 176), "PROD002 主图"),
        ("PROD002_detail_1.jpg", (0, 188, 212), "PROD002 详情1"),
    ]

    for filename, color, text in images_to_create:
        create_image(filename, color, text)

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

    print("\n所有示例数据创建完成！")


if __name__ == "__main__":
    create_sample_data()
