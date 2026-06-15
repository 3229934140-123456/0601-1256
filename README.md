# 电商运营平台 - 商品上架资料检查工具

供品牌运营人员批量检查商品上架资料的命令行工具。在上架前快速扫描商品资料，发现问题并自动修复可修复项。

## 功能特性

- 📁 **scan** - 扫描商品资料文件夹，读取 Excel/CSV 数据
- 🔍 **check** - 全面检查商品资料完整性和规范性
- 🔧 **fix** - 自动修复可修复的问题，预览修正内容
- 📊 **report** - 导出多种格式的检查报告

### 检查项

| 检查项 | 描述 | 错误级别 | 可自动修复 |
|--------|------|----------|------------|
| 主图缺失 | 检查商品主图是否存在 | 严重 | ❌ |
| 详情图缺失 | 检查商品详情图是否存在（建议≥3张） | 警告/提示 | ❌ |
| 标题超长 | 标题超过60字符 | 警告 | ✅ |
| 敏感词检测 | 检测广告法禁用敏感词 | 警告 | ✅ |
| 价格格式 | 价格为空或超出区间[0.1, 999999] | 严重/警告 | ❌ |
| 库存格式 | 库存为空、负数或为0 | 严重/提示 | ❌ |
| 商品编码重复 | SKU编码重复 | 严重 | ❌ |
| 商品编码格式 | SKU应为6-20位字母数字组合 | 警告 | ❌ |
| 类目缺失 | 自动根据标题关键词补全类目 | 警告 | ✅ |
| 标题缺失 | 商品标题为空 | 严重 | ❌ |

## 安装

```bash
pip install -e .
```

## 目录结构

```
ecommerce_checker/
├── __init__.py          # 包初始化
├── cli.py               # 命令行入口
├── config.py            # 配置（敏感词、规则等）
├── models.py            # 数据模型
├── reader.py            # 数据读取模块
├── checker.py           # 检查逻辑模块
├── fixer.py             # 自动修复模块
├── reporter.py          # 报告生成模块
└── utils.py             # 工具函数
```

## 商品资料目录结构

```
商品资料目录/
├── products.xlsx       # 商品数据文件（支持 .xlsx, .xls, .csv）
└── images/             # 图片目录
    ├── PROD001_main.jpg       # 主图（{sku}_main.* 或 {sku}.*）
    ├── PROD001_detail_1.jpg   # 详情图1
    ├── PROD001_detail_2.jpg   # 详情图2
    └── ...
```

### Excel 列名支持

工具自动识别以下列名（支持中英文）：

| 标准字段 | 支持的列名 |
|---------|-----------|
| SKU | sku, 商品编码, 商品编号, 货号, 编码, product_id |
| 标题 | title, 标题, 商品名称, 商品标题, 名称, product_name |
| 价格 | price, 价格, 售价, 单价, 商品价格, sale_price |
| 库存 | stock, 库存, 数量, 库存数量, inventory, quantity |
| 类目 | category, 类目, 分类, 商品分类, 商品类目, 品类 |
| 店铺 | shop, 店铺, 商店, 门店, store |

## 使用指南

### 1. 扫描商品资料

```bash
# 快速扫描
ecommerce-checker scan sample_data

# 显示详细商品列表
ecommerce-checker scan sample_data --detail
```

### 2. 检查商品资料

```bash
# 完整检查
ecommerce-checker check sample_data

# 仅显示摘要
ecommerce-checker check sample_data --summary

# 按店铺过滤
ecommerce-checker check sample_data --store 旗舰店

# 按错误级别过滤
ecommerce-checker check sample_data --level critical
```

### 3. 自动修复

```bash
# 预览修复内容（不实际修改）
ecommerce-checker fix sample_data --preview

# 执行修复（需要确认）
ecommerce-checker fix sample_data

# 跳过确认，直接修复
ecommerce-checker fix sample_data -y

# 指定输出目录
ecommerce-checker fix sample_data --output output_dir
```

### 4. 导出报告

```bash
# 导出 Excel 报告
ecommerce-checker report sample_data --format excel

# 导出 JSON 报告
ecommerce-checker report sample_data --format json

# 同时生成待修改清单
ecommerce-checker report sample_data --fix-list

# 按店铺过滤
ecommerce-checker report sample_data --store 旗舰店 --fix-list

# 按错误级别过滤
ecommerce-checker report sample_data --level warning

# 指定输出路径
ecommerce-checker report sample_data --output reports/my_report.xlsx

# 生成后自动打开
ecommerce-checker report sample_data --open
```

## 配置说明

### 敏感词配置

在 [config.py](ecommerce_checker/config.py#L4-L15) 中修改 `SENSITIVE_WORDS` 列表：

```python
SENSITIVE_WORDS = [
    "最", "第一", "绝对", "国家级", "最高级",
    "全网最低", "秒杀", "爆款", "限量", "独家",
]
```

### 类目自动匹配规则

在 [config.py](ecommerce_checker/config.py#L22-L31) 中配置 `CATEGORY_RULES`：

```python
CATEGORY_RULES = {
    "服装": ["上衣", "裤子", "裙子", "外套", "T恤", "衬衫", "卫衣", "毛衣"],
    "鞋靴": ["鞋子", "运动鞋", "皮鞋", "靴子", "凉鞋", "拖鞋"],
    # ...
}
```

### 其他配置

| 配置项 | 默认值 | 说明 |
|-------|--------|------|
| TITLE_MAX_LENGTH | 60 | 标题最大字符数 |
| PRICE_MIN / PRICE_MAX | 0.1 / 999999 | 价格合理区间 |
| IMAGE_EXTENSIONS | [.jpg, .jpeg, .png, .webp] | 支持的图片格式 |

## 示例数据

项目包含示例数据用于测试：

```bash
# 生成示例数据
python generate_sample_data.py

# 测试扫描
ecommerce-checker scan sample_data --detail

# 测试检查
ecommerce-checker check sample_data

# 测试修复
ecommerce-checker fix sample_data --preview

# 测试报告
ecommerce-checker report sample_data --fix-list
```

## 输出文件说明

### 检查报告 (check_report.xlsx)

包含所有问题的详细清单，字段包括：
- 商品编码、商品标题、店铺
- 问题字段、问题类型、问题描述
- 错误级别、修复建议、可自动修复
- 来源文件

### 待修改清单 (fix_list.xlsx)

按商品分组的待修改项，便于运营人员逐一处理：
- 商品编码、商品标题、店铺
- 问题数量
- 待修改内容
- 修复建议

### 修复预览 (fix_preview.xlsx)

自动修复内容的对比：
- 商品编码、修改字段
- 原值、新值
- 修改原因

### 修复后数据 (products_fixed.xlsx)

应用自动修复后的商品数据。

## 工作流程建议

1. **扫描** → `ecommerce-checker scan <目录> --detail` 确认数据读取正确
2. **检查** → `ecommerce-checker check <目录> --summary` 了解整体情况
3. **详情** → `ecommerce-checker check <目录> --level critical` 关注严重问题
4. **修复** → `ecommerce-checker fix <目录> --preview` 预览修复内容
5. **确认** → `ecommerce-checker fix <目录>` 执行自动修复
6. **报告** → `ecommerce-checker report <目录> --fix-list` 导出报告和待修改清单
7. **人工处理** → 根据待修改清单处理无法自动修复的问题
8. **复查** → 修复后重新运行 `check` 确认所有问题已解决

## 开发

```bash
# 安装开发依赖
pip install -r requirements.txt

# 安装到本地
pip install -e .

# 运行测试
python -m pytest tests/
```

## 常见问题

**Q: 图片命名有什么要求？**
A: 主图使用 `{SKU}_main.jpg` 或 `{SKU}.jpg`，详情图使用 `{SKU}_detail_1.jpg`, `{SKU}_detail_2.jpg` 等。

**Q: 支持哪些数据文件格式？**
A: 支持 `.xlsx`, `.xls`, `.csv` 格式，会自动识别列名。

**Q: 可以只检查某个店铺的商品吗？**
A: 可以，使用 `--store <店铺名>` 参数过滤。

**Q: 自动修复会覆盖原始数据吗？**
A: 不会，修复后的数据会保存到新的文件中，原始数据保持不变。

**Q: 如何添加自定义敏感词？**
A: 修改 `ecommerce_checker/config.py` 中的 `SENSITIVE_WORDS` 列表。

## License

MIT
