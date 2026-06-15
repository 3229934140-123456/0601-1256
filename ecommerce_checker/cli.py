from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from .checker import ProductChecker
from .config import ERROR_LEVELS
from .config_loader import load_config
from .fixer import ProductFixer
from .reader import ProductReader
from .reporter import ReportGenerator
from .baseline import (
    add_history,
    build_current_record,
    export_history,
    load_baseline,
    load_history,
    save_baseline,
)
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

        checker = ProductChecker(scan_result.products, base_dir=folder_path, config=load_config(folder_path))
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

        current = build_current_record(scan_result, check_results)
        add_history(folder_path, current)

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

        checker = ProductChecker(scan_result.products, base_dir=folder_path, config=load_config(folder_path))
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

        output = os.path.normpath(output)
        if not os.path.isabs(output):
            has_sep = os.sep in output or "/" in output
            if not has_sep:
                output = os.path.join(folder_path, output)
                output = os.path.normpath(output)

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

        checker = ProductChecker(scan_result.products, base_dir=folder_path, config=load_config(folder_path))
        check_results = checker.check_all(store_filter=store)

        reporter = ReportGenerator(scan_result, check_results)

        if not output:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
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

        current = build_current_record(scan_result, check_results)
        add_history(folder_path, current)

        if open_file:
            try:
                os.startfile(saved_path)
            except AttributeError:
                click.launch(saved_path)

    except Exception as e:
        console.print(f"[bold red]报告生成失败: {e}[/bold red]")
        raise click.Abort()


@cli.command()
@click.argument("folder_path", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option("--store", help="按店铺过滤")
def diff(folder_path: str, store: Optional[str]) -> None:
    """与上次检查记录对比，查看商品数和问题数变化"""
    try:
        prev = load_baseline(folder_path)
        if prev is None:
            console.print("[yellow]尚未设置基准，无法对比[/yellow]")
            console.print("[yellow]请先运行 [bold]save-baseline[/bold] 命令保存当前结果为基准，再使用 diff 对比后续变化[/yellow]")
            return

        reader = ProductReader(folder_path)
        scan_result = reader.read_products()

        if not scan_result.products:
            console.print("[yellow]未找到商品数据[/yellow]")
            return

        checker = ProductChecker(scan_result.products, base_dir=folder_path, config=load_config(folder_path))
        check_results = checker.check_all(store_filter=store)

        current = build_current_record(scan_result, check_results)

        console.print(f"\n[bold blue]=== 对比结果 ===[/bold blue]")
        console.print(f"上次记录时间: [dim]{prev.timestamp}[/dim]")
        console.print(f"本次检查时间: [dim]{current.timestamp}[/dim]")
        console.print("")

        table = Table(title="数量对比", show_lines=True)
        table.add_column("指标", style="bold")
        table.add_column("上次", style="cyan", justify="right")
        table.add_column("本次", style="green", justify="right")
        table.add_column("变化", justify="center")

        def _fmt_delta(cur: int, old: int) -> str:
            d = cur - old
            if d > 0:
                return f"[red]+{d}[/red]"
            elif d < 0:
                return f"[green]{d}[/green]"
            return "[dim]0[/dim]"

        table.add_row("商品文件数", str(prev.total_files), str(current.total_files), _fmt_delta(current.total_files, prev.total_files))
        table.add_row("商品总数", str(prev.total_products), str(current.total_products), _fmt_delta(current.total_products, prev.total_products))
        table.add_row("通过检查", str(prev.passed_count), str(current.passed_count), _fmt_delta(current.passed_count, prev.passed_count))
        table.add_row("存在问题", str(prev.failed_count), str(current.failed_count), _fmt_delta(current.failed_count, prev.failed_count))
        table.add_row("问题总数", str(prev.total_issues), str(current.total_issues), _fmt_delta(current.total_issues, prev.total_issues))
        table.add_row("严重问题", str(prev.critical_count), str(current.critical_count), _fmt_delta(current.critical_count, prev.critical_count))
        table.add_row("警告问题", str(prev.warning_count), str(current.warning_count), _fmt_delta(current.warning_count, prev.warning_count))
        table.add_row("提示问题", str(prev.info_count), str(current.info_count), _fmt_delta(current.info_count, prev.info_count))

        console.print(table)

        stable = (
            current.total_files == prev.total_files
            and current.total_products == prev.total_products
            and current.total_issues == prev.total_issues
            and current.critical_count == prev.critical_count
        )

        if stable:
            console.print("\n[bold green]✓ 数据稳定：商品数、问题数、严重问题数与上次一致，无报告文件混入[/bold green]")
        else:
            console.print("\n[bold yellow]⚠ 数据有变化：请确认是否修改了商品资料，或检查是否有报告/修复文件被误读[/bold yellow]")

    except Exception as e:
        console.print(f"[bold red]对比失败: {e}[/bold red]")
        raise click.Abort()


@cli.command()
@click.argument("folder_path", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option("--store", help="按店铺过滤")
@click.option("--save-baseline", "save_bl", is_flag=True, help="验收通过后自动保存为基准")
def accept(folder_path: str, store: Optional[str], save_bl: bool) -> None:
    """完整验收：依次执行扫描、检查、修复预览、报告、对比、历史查看"""
    try:
        console.print("[bold blue]╔══════════════════════════════════════════╗[/bold blue]")
        console.print("[bold blue]║        电商商品资料完整验收流程          ║[/bold blue]")
        console.print("[bold blue]╚══════════════════════════════════════════╝[/bold blue]")
        console.print(f"验收目录: [green]{folder_path}[/green]\n")

        reader = ProductReader(folder_path)
        scan_result = reader.read_products()
        config = load_config(folder_path)

        console.print("[bold cyan]━━━ 步骤 1/6: 扫描商品资料 ━━━[/bold cyan]")
        console.print(f"  发现文件: [yellow]{scan_result.total_files}[/yellow] 个")
        console.print(f"  商品总数: [yellow]{scan_result.total_products}[/yellow] 个")
        if scan_result.stores:
            console.print(f"  涉及店铺: [cyan]{', '.join(scan_result.stores)}[/cyan]")
        if scan_result.errors:
            console.print(f"  [red]读取错误: {len(scan_result.errors)} 个[/red]")
        console.print("")

        if not scan_result.products:
            console.print("[bold red]未找到商品数据，验收中止[/bold red]")
            return

        checker = ProductChecker(scan_result.products, base_dir=folder_path, config=config)
        check_results = checker.check_all(store_filter=store)

        critical = sum(1 for r in check_results for i in r.issues if i.level == "critical")
        warning = sum(1 for r in check_results for i in r.issues if i.level == "warning")
        info = sum(1 for r in check_results for i in r.issues if i.level == "info")
        passed = sum(1 for r in check_results if r.passed)
        failed = len(check_results) - passed
        total_issues = critical + warning + info

        console.print("[bold cyan]━━━ 步骤 2/6: 检查商品资料 ━━━[/bold cyan]")
        console.print(f"  检查商品数: [yellow]{len(check_results)}[/yellow]")
        console.print(f"  通过: [green]{passed}[/green]  |  存在问题: [red]{failed}[/red]")
        console.print(f"  问题总数: [yellow]{total_issues}[/yellow]  (严重: [red]{critical}[/red]  警告: [yellow]{warning}[/yellow]  提示: [blue]{info}[/blue])")
        if critical > 0:
            console.print(f"  [bold red]⚠ 存在 {critical} 个严重问题[/bold red]")
        console.print("")

        fixer = ProductFixer(scan_result.products)
        previews = fixer.preview_fixes(check_results)

        console.print("[bold cyan]━━━ 步骤 3/6: 修复预览 ━━━[/bold cyan]")
        console.print(f"  可自动修复项: [yellow]{len(previews)}[/yellow] 个")
        if previews:
            for p in previews[:5]:
                console.print(f"    {p.sku} | {p.field}: {str(p.old_value)[:15]} → {str(p.new_value)[:15]}")
            if len(previews) > 5:
                console.print(f"    ... 还有 {len(previews) - 5} 项")
        else:
            console.print("  [green]无可自动修复项[/green]")
        console.print("")

        reporter = ReportGenerator(scan_result, check_results)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(folder_path, f"check_report_{timestamp}.xlsx")
        reporter.export_excel(report_path)
        fix_list_path = os.path.join(folder_path, f"fix_list_{timestamp}.xlsx")
        reporter.export_fix_list(fix_list_path)

        console.print("[bold cyan]━━━ 步骤 4/6: 导出报告 ━━━[/bold cyan]")
        console.print(f"  检查报告: [green]{report_path}[/green]")
        console.print(f"  待修改清单: [green]{fix_list_path}[/green]")
        console.print("")

        console.print("[bold cyan]━━━ 步骤 5/6: 对比基准 ━━━[/bold cyan]")
        prev = load_baseline(folder_path)
        if prev is None:
            console.print("  [yellow]⚠ 尚未设置基准[/yellow]")
            console.print("  [yellow]请使用 save-baseline 命令确认当前结果后保存基准[/yellow]")
        else:
            current = build_current_record(scan_result, check_results)
            try:
                dt = datetime.fromisoformat(prev.timestamp)
                bl_time = dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                bl_time = prev.timestamp

            table = Table(show_lines=True)
            table.add_column("指标", style="bold")
            table.add_column("基准", style="cyan", justify="right")
            table.add_column("本次", style="green", justify="right")
            table.add_column("变化", justify="center")

            def _fmt_delta(cur: int, old: int) -> str:
                d = cur - old
                if d > 0:
                    return f"[red]+{d}[/red]"
                elif d < 0:
                    return f"[green]{d}[/green]"
                return "[dim]0[/dim]"

            table.add_row("商品总数", str(prev.total_products), str(current.total_products), _fmt_delta(current.total_products, prev.total_products))
            table.add_row("问题总数", str(prev.total_issues), str(current.total_issues), _fmt_delta(current.total_issues, prev.total_issues))
            table.add_row("严重问题", str(prev.critical_count), str(current.critical_count), _fmt_delta(current.critical_count, prev.critical_count))
            table.add_row("警告问题", str(prev.warning_count), str(current.warning_count), _fmt_delta(current.warning_count, prev.warning_count))
            console.print(table)
            console.print(f"  基准时间: [dim]{bl_time}[/dim]")

            stable = (
                current.total_products == prev.total_products
                and current.total_issues == prev.total_issues
                and current.critical_count == prev.critical_count
            )
            if stable:
                console.print("  [bold green]✓ 数据稳定[/bold green]")
            else:
                console.print("  [bold yellow]⚠ 数据有变化，请确认[/bold yellow]")
        console.print("")

        current = build_current_record(scan_result, check_results)
        add_history(folder_path, current)

        console.print("[bold cyan]━━━ 步骤 6/6: 历史趋势 ━━━[/bold cyan]")
        records = load_history(folder_path, limit=5)
        if records:
            for idx, rec in enumerate(reversed(records)):
                try:
                    dt = datetime.fromisoformat(rec.timestamp)
                    t = dt.strftime("%m-%d %H:%M")
                except Exception:
                    t = rec.timestamp
                console.print(f"  {t}  商品={rec.total_products}  问题={rec.total_issues}  严重={rec.critical_count}  警告={rec.warning_count}")
        else:
            console.print("  [dim]暂无历史记录[/dim]")
        console.print("")

        console.print("[bold blue]╔══════════════════════════════════════════╗[/bold blue]")
        console.print("[bold green]  ✓ 验收流程完成[/bold green]")
        console.print(f"  商品: {scan_result.total_products}  问题: {total_issues}  严重: {critical}  警告: {warning}  提示: {info}")
        if critical > 0:
            console.print("[bold red]  ⚠ 存在严重问题，建议修复后再次验收[/bold red]")
        if prev is None:
            console.print("[bold yellow]  ⚠ 尚未设置基准，确认结果后请运行 save-baseline[/bold yellow]")
        console.print("[bold blue]╚══════════════════════════════════════════╝[/bold blue]")

        if save_bl and critical == 0:
            record = save_baseline(folder_path, scan_result, check_results)
            console.print(f"\n[bold green]✓ 已自动保存为基准 (时间: {record.timestamp})[/bold green]")

    except Exception as e:
        console.print(f"[bold red]验收失败: {e}[/bold red]")
        raise click.Abort()


@cli.command("save-baseline")
@click.argument("folder_path", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option("--yes", "-y", is_flag=True, help="跳过确认直接保存")
def save_baseline_cmd(folder_path: str, yes: bool) -> None:
    """手动保存当前检查结果为对比基准"""
    try:
        reader = ProductReader(folder_path)
        scan_result = reader.read_products()

        if not scan_result.products:
            console.print("[yellow]未找到商品数据[/yellow]")
            return

        checker = ProductChecker(scan_result.products, base_dir=folder_path, config=load_config(folder_path))
        check_results = checker.check_all()

        critical = sum(1 for r in check_results for i in r.issues if i.level == "critical")
        warning = sum(1 for r in check_results for i in r.issues if i.level == "warning")
        info = sum(1 for r in check_results for i in r.issues if i.level == "info")
        passed = sum(1 for r in check_results if r.passed)
        failed = len(check_results) - passed

        console.print("\n[bold blue]=== 当前批次摘要 ===[/bold blue]")
        console.print(f"  商品总数: [yellow]{scan_result.total_products}[/yellow]")
        console.print(f"  通过检查: [green]{passed}[/green]  |  存在问题: [red]{failed}[/red]")
        console.print(f"  问题总数: [yellow]{critical + warning + info}[/yellow]  (严重: [red]{critical}[/red]  警告: [yellow]{warning}[/yellow]  提示: [blue]{info}[/blue])")
        if scan_result.stores:
            console.print(f"  涉及店铺: [cyan]{', '.join(scan_result.stores)}[/cyan]")

        if critical > 0:
            console.print(f"\n  [bold yellow]⚠ 存在 {critical} 个严重问题，建议先修复后再保存基准[/bold yellow]")

        existing = load_baseline(folder_path)
        if existing:
            try:
                dt = datetime.fromisoformat(existing.timestamp)
                bl_time = dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                bl_time = existing.timestamp
            console.print(f"\n  [dim]当前基准时间: {bl_time}[/dim]")
            console.print(f"  [dim]保存将覆盖已有基准[/dim]")

        if not yes:
            console.print("")
            click.confirm("确认保存当前结果为基准?", default=False, abort=True)

        record = save_baseline(folder_path, scan_result, check_results)
        console.print(f"\n[bold green]✓ 基准已保存[/bold green]")
        console.print(f"  保存时间: {record.timestamp}")
        console.print(f"  商品总数: {record.total_products}")
        console.print(f"  问题总数: {record.total_issues}")
        console.print(f"  严重问题: {record.critical_count}")

        current = build_current_record(scan_result, check_results)
        add_history(folder_path, current)

    except click.Abort:
        console.print("[yellow]已取消保存基准[/yellow]")
    except Exception as e:
        console.print(f"[bold red]保存基准失败: {e}[/bold red]")
        raise click.Abort()


@cli.command("show-config")
@click.argument("folder_path", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option("--shop", help="查看指定店铺的生效规则")
def show_config(folder_path: str, shop: Optional[str]) -> None:
    """打印当前资料目录的检查规则配置"""
    try:
        config = load_config(folder_path)

        if config.config_file_path:
            console.print(f"[bold blue]=== 规则配置 ===[/bold blue]")
            console.print(f"配置文件: [green]{config.config_file_path}[/green]")
        else:
            console.print(f"[bold blue]=== 规则配置（使用默认值） ===[/bold blue]")
            console.print("[dim]未找到配置文件，所有规则使用默认值[/dim]")
        console.print("")

        _print_config_table("全局默认", config.global_config)

        if shop:
            effective = config.get_effective_config(shop)
            _print_config_table(f"店铺: {shop}", effective)

            global_cfg = config.global_config
            overrides = []
            for key in effective:
                if key in ("category_rules", "image_extensions"):
                    continue
                if effective.get(key) != global_cfg.get(key):
                    overrides.append(key)
            if overrides:
                console.print(f"  [yellow]以下规则覆盖了全局默认: {', '.join(overrides)}[/yellow]")
            else:
                console.print(f"  [dim]该店铺未覆盖全局默认规则[/dim]")
            console.print("")
        elif config.configured_shops:
            console.print(f"[bold]已配置覆盖规则的店铺:[/bold] [cyan]{', '.join(config.configured_shops)}[/cyan]")
            for shop_name in config.configured_shops:
                console.print(f"\n  [bold]店铺: {shop_name}[/bold]")
                effective = config.get_effective_config(shop_name)
                global_cfg = config.global_config
                overrides = []
                for key in effective:
                    if key in ("category_rules", "image_extensions"):
                        continue
                    if effective.get(key) != global_cfg.get(key):
                        overrides.append(key)
                if overrides:
                    console.print(f"    [yellow]覆盖规则: {', '.join(overrides)}[/yellow]")
                else:
                    console.print(f"    [dim]未覆盖全局默认规则[/dim]")
            console.print("\n[yellow]使用 --shop <店铺名> 查看指定店铺的完整生效规则[/yellow]")

    except Exception as e:
        console.print(f"[bold red]查看配置失败: {e}[/bold red]")
        raise click.Abort()


def _print_config_table(label: str, cfg: dict) -> None:
    console.print(f"[bold]{label}[/bold]")

    table = Table(show_lines=True)
    table.add_column("规则项", style="bold")
    table.add_column("值", style="green")

    simple_keys = [
        ("标题最大长度", "title_max_length"),
        ("最低价格", "price_min"),
        ("最高价格", "price_max"),
        ("详情图最低张数", "detail_images_min_count"),
        ("图片最小宽度(px)", "image_min_width"),
        ("图片最小高度(px)", "image_min_height"),
        ("图片最大大小(MB)", "image_max_size_mb"),
    ]

    for name, key in simple_keys:
        table.add_row(name, str(cfg.get(key, "-")))

    sensitive_words = cfg.get("sensitive_words", [])
    if sensitive_words:
        words_str = ", ".join(str(w) for w in sensitive_words[:10])
        if len(sensitive_words) > 10:
            words_str += f" ... 共{len(sensitive_words)}个"
        table.add_row("敏感词列表", words_str)
    else:
        table.add_row("敏感词列表", "(无)")

    category_rules = cfg.get("category_rules", {})
    if category_rules:
        rules_str = ", ".join(f"{k}({len(v)}词)" for k, v in category_rules.items())
        table.add_row("类目规则", rules_str)
    else:
        table.add_row("类目规则", "(无)")

    console.print(table)
    console.print("")


@cli.command()
@click.argument("folder_path", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option("--limit", type=int, default=10, help="显示最近的N条记录")
def history(folder_path: str, limit: int) -> None:
    """查看最近的检查历史记录"""
    try:
        records = load_history(folder_path, limit=limit)

        if not records:
            console.print("[yellow]没有历史记录，请先运行 check 或 report 命令[/yellow]")
            return

        console.print(f"\n[bold blue]=== 检查历史（最近 {len(records)} 条） ===[/bold blue]")

        table = Table(title="检查历史", show_lines=True)
        table.add_column("序号", style="bold", justify="right")
        table.add_column("时间", style="cyan")
        table.add_column("商品数", justify="right")
        table.add_column("通过", justify="right", style="green")
        table.add_column("问题", justify="right", style="red")
        table.add_column("严重", justify="right", style="red")
        table.add_column("警告", justify="right", style="yellow")
        table.add_column("提示", justify="right", style="blue")

        for idx, record in enumerate(reversed(records)):
            try:
                dt = datetime.fromisoformat(record.timestamp)
                time_str = dt.strftime("%m-%d %H:%M")
            except Exception:
                time_str = record.timestamp

            table.add_row(
                str(len(records) - idx),
                time_str,
                str(record.total_products),
                str(record.passed_count),
                str(record.failed_count),
                str(record.critical_count),
                str(record.warning_count),
                str(record.info_count),
            )

        console.print(table)

        baseline = load_baseline(folder_path)
        if baseline:
            try:
                dt = datetime.fromisoformat(baseline.timestamp)
                baseline_time = dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                baseline_time = baseline.timestamp
            console.print(f"\n[dim]当前基准时间: {baseline_time}[/dim]")
        else:
            console.print(f"\n[dim]尚未设置基准，使用 save-baseline 命令手动设置[/dim]")

    except Exception as e:
        console.print(f"[bold red]查看历史失败: {e}[/bold red]")
        raise click.Abort()


@cli.command("history-export")
@click.argument("folder_path", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option("--output", help="输出文件路径")
@click.option("--limit", type=int, default=50, help="导出最近的N条记录")
def history_export_cmd(folder_path: str, output: Optional[str], limit: int) -> None:
    """导出检查历史记录为 Excel"""
    try:
        if not output:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output = os.path.join(folder_path, f"check_history_{timestamp}.xlsx")

        saved_path = export_history(folder_path, output, limit=limit)
        console.print(f"\n[bold green]✓ 历史记录已导出: {saved_path}[/bold green]")

    except Exception as e:
        console.print(f"[bold red]导出历史失败: {e}[/bold red]")
        raise click.Abort()


if __name__ == "__main__":
    cli()
