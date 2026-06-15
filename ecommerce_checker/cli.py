from __future__ import annotations

import os
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from .checker import ProductChecker
from .config import ERROR_LEVELS
from .fixer import ProductFixer
from .reader import ProductReader
from .reporter import ReportGenerator
from . import __version__

console = Console()


@click.group()
@click.version_option(__version__)
def cli() -> None:
    """电商运营平台 - 商品上架资料批量检查工具"""
    pass


@cli.command()
@click.argument("folder_path", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option("--detail", is_flag=True, help="显示详细商品列表")
def scan(folder_path: str, detail: bool) -> None:
    """扫描商品资料文件夹"""
    try:
        reader = ProductReader(folder_path)
        scan_result = reader.read_products()

        console.print(f"\n[bold blue]=== 扫描结果 ===[/bold blue]")
        console.print(f"扫描路径: [green]{folder_path}[/green]")
        console.print(f"发现文件: [yellow]{scan_result.total_files}[/yellow] 个")
        console.print(f"商品总数: [yellow]{scan_result.total_products}[/yellow] 个")

        if scan_result.stores:
            console.print(f"涉及店铺: [cyan]{', '.join(scan_result.stores)}[/cyan]")

        if scan_result.categories:
            console.print(f"涉及类目: [cyan]{', '.join(scan_result.categories)}[/cyan]")

        if scan_result.errors:
            console.print("\n[bold red]读取错误:[/bold red]")
            for error in scan_result.errors:
                console.print(f"  [red]- {error}[/red]")

        if detail and scan_result.products:
            table = Table(title="商品列表", show_lines=True)
            table.add_column("SKU", style="cyan", no_wrap=True)
            table.add_column("标题", style="green")
            table.add_column("价格", style="yellow", justify="right")
            table.add_column("库存", style="magenta", justify="right")
            table.add_column("类目", style="blue")
            table.add_column("店铺", style="red")
            table.add_column("主图", style="white")
            table.add_column("详情图", style="white", justify="right")

            for product in scan_result.products:
                table.add_row(
                    product.sku,
                    product.title[:30] + "..." if len(product.title) > 30 else product.title,
                    f"¥{product.price:.2f}" if product.price else "-",
                    str(product.stock) if product.stock is not None else "-",
                    product.category or "-",
                    product.shop or "-",
                    "✓" if product.main_image else "✗",
                    str(len(product.detail_images)),
                )
            console.print(table)

    except Exception as e:
        console.print(f"[bold red]扫描失败: {e}[/bold red]")
        raise click.Abort()


@cli.command()
@click.argument("folder_path", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option("--store", help="按店铺过滤检查结果")
@click.option("--level", type=click.Choice(["critical", "warning", "info"]), help="按错误级别过滤")
@click.option("--summary", is_flag=True, help="仅显示统计摘要")
def check(folder_path: str, store: Optional[str], level: Optional[str], summary: bool) -> None:
    """检查商品资料完整性和规范性"""
    try:
        reader = ProductReader(folder_path)
        scan_result = reader.read_products()

        if not scan_result.products:
            console.print("[yellow]未找到商品数据[/yellow]")
            return

        checker = ProductChecker(scan_result.products)
        check_results = checker.check_all(store_filter=store)

        if not check_results:
            console.print("[yellow]没有匹配的检查结果[/yellow]")
            return

        reporter = ReportGenerator(scan_result, check_results)

        if summary:
            _print_check_summary(check_results, store)
        else:
            report = reporter.generate_console_report(level_filter=level)
            console.print(report)

        critical_count = sum(1 for r in check_results for i in r.issues if i.level == "critical")
        if critical_count > 0:
            console.print(f"\n[bold red]存在 {critical_count} 个严重问题，建议先修复后再上架[/bold red]")

    except Exception as e:
        console.print(f"[bold red]检查失败: {e}[/bold red]")
        raise click.Abort()


def _print_check_summary(check_results, store: Optional[str]) -> None:
    total = len(check_results)
    passed = sum(1 for r in check_results if r.passed)
    failed = total - passed
    total_issues = sum(len(r.issues) for r in check_results)

    level_stats = {}
    for result in check_results:
        for issue in result.issues:
            level_stats[issue.level] = level_stats.get(issue.level, 0) + 1

    console.print(f"\n[bold blue]=== 检查摘要 ===[/bold blue]")
    if store:
        console.print(f"过滤店铺: [cyan]{store}[/cyan]")
    console.print(f"检查商品数: [yellow]{total}[/yellow]")
    console.print(f"通过: [green]{passed}[/green] 个")
    console.print(f"存在问题: [red]{failed}[/red] 个")
    console.print(f"问题总数: [yellow]{total_issues}[/yellow] 个")

    if level_stats:
        console.print("\n[bold]问题分级:[/bold]")
        for level, count in level_stats.items():
            level_name = ERROR_LEVELS.get(level, level)
            color = {"critical": "red", "warning": "yellow", "info": "blue"}.get(level, "white")
            console.print(f"  [{color}]{level_name}[/{color}]: {count} 个")

    if failed > 0:
        console.print(f"\n  通过率: [yellow]{(passed/total*100):.1f}%[/yellow]")


@cli.command()
@click.argument("folder_path", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option("--store", help="按店铺过滤")
@click.option("--preview", is_flag=True, help="仅预览修复内容，不实际修改")
@click.option("--output", default="fixed_data", help="修复后数据输出目录")
@click.option("--yes", "-y", is_flag=True, help="跳过确认，直接执行修复")
def fix(folder_path: str, store: Optional[str], preview: bool, output: str, yes: bool) -> None:
    """自动修复可修复的问题"""
    try:
        reader = ProductReader(folder_path)
        scan_result = reader.read_products()

        if not scan_result.products:
            console.print("[yellow]未找到商品数据[/yellow]")
            return

        checker = ProductChecker(scan_result.products)
        check_results = checker.check_all(store_filter=store)

        fixer = ProductFixer(scan_result.products)
        previews = fixer.preview_fixes(check_results)

        if not previews:
            console.print("[green]没有可自动修复的问题[/green]")
            return

        console.print(f"\n[bold blue]=== 修复预览 ===[/bold blue]")
        console.print(f"可自动修复项: [yellow]{len(previews)}[/yellow] 个")

        table = Table(title="自动修复内容")
        table.add_column("SKU", style="cyan")
        table.add_column("字段", style="blue")
        table.add_column("原值", style="red")
        table.add_column("新值", style="green")
        table.add_column("原因", style="yellow")

        for p in previews[:20]:
            table.add_row(
                p.sku,
                p.field,
                str(p.old_value)[:20] if p.old_value else "-",
                str(p.new_value)[:20],
                p.reason[:40] if len(p.reason) > 40 else p.reason,
            )
        if len(previews) > 20:
            table.add_row("...", "...", "...", "...", f"... 还有 {len(previews) - 20} 项")
        console.print(table)

        if preview:
            return

        if not yes:
            click.confirm(f"\n确认应用以上 {len(previews)} 项修复?", default=False, abort=True)

        applied, skipped = fixer.apply_fixes(check_results, preview=False)
        console.print(f"\n[green]已应用 {len(applied)} 项修复[/green]")

        if not os.path.isabs(output):
            output = os.path.join(folder_path, output)

        saved_files = fixer.save_fixes(output)
        console.print(f"\n[bold]修复后的数据已保存到:[/bold]")
        for f in saved_files:
            console.print(f"  [green]{f}[/green]")

        reporter = ReportGenerator(scan_result, check_results)
        preview_file = os.path.join(output, "fix_preview.xlsx")
        reporter.export_fix_preview(previews, preview_file)
        console.print(f"修复预览已导出: [cyan]{preview_file}[/cyan]")

        fix_list_file = os.path.join(output, "fix_list.xlsx")
        reporter.export_fix_list(fix_list_file)
        console.print(f"待修改清单已导出: [cyan]{fix_list_file}[/cyan]")

    except Exception as e:
        console.print(f"[bold red]修复失败: {e}[/bold red]")
        raise click.Abort()


@cli.command()
@click.argument("folder_path", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option("--store", help="按店铺过滤")
@click.option("--level", type=click.Choice(["critical", "warning", "info"]), help="按错误级别过滤")
@click.option("--format", "output_format", type=click.Choice(["excel", "json"]), default="excel", help="报告格式")
@click.option("--output", help="输出文件路径")
@click.option("--fix-list", is_flag=True, help="同时生成待修改清单")
@click.option("--open", "open_file", is_flag=True, help="生成后打开文件")
def report(folder_path: str, store: Optional[str], level: Optional[str], output_format: str, output: Optional[str], fix_list: bool, open_file: bool) -> None:
    """导出检查报告"""
    try:
        reader = ProductReader(folder_path)
        scan_result = reader.read_products()

        if not scan_result.products:
            console.print("[yellow]未找到商品数据[/yellow]")
            return

        checker = ProductChecker(scan_result.products)
        check_results = checker.check_all(store_filter=store)

        reporter = ReportGenerator(scan_result, check_results)

        if not output:
            timestamp = scan_result.products[0].source_file.split("_")[-1].split(".")[0] if scan_result.products else "report"
            ext = "xlsx" if output_format == "excel" else "json"
            output = os.path.join(folder_path, f"check_report_{timestamp}.{ext}")

        if output_format == "excel":
            saved_path = reporter.export_excel(output, level_filter=level)
        else:
            saved_path = reporter.export_json(output, level_filter=level)

        console.print(f"\n[green]检查报告已导出: {saved_path}[/green]")

        if fix_list:
            fix_list_path = os.path.splitext(saved_path)[0] + "_fix_list.xlsx"
            reporter.export_fix_list(fix_list_path, level_filter=level)
            console.print(f"[green]待修改清单已导出: {fix_list_path}[/green]")

        console_report = reporter.generate_console_report(level_filter=level)
        console.print(console_report)

        if open_file:
            try:
                os.startfile(saved_path)
            except AttributeError:
                click.launch(saved_path)

    except Exception as e:
        console.print(f"[bold red]报告生成失败: {e}[/bold red]")
        raise click.Abort()


if __name__ == "__main__":
    cli()
