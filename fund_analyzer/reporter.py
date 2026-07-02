"""
报告生成模块
==========
将基金分析结果输出为可读的文本、表格和 Markdown 报告。

功能:
    - fund_summary: 简洁文本摘要
    - fund_comparison: 多基金对比表格
    - export_to_csv: 导出净值数据
    - generate_report: 生成 Markdown 完整报告
"""

import os
from datetime import datetime
from typing import Optional

import pandas as pd

from . import fetcher
from . import analyzer
from . import portfolio as pf


# ---------------------------------------------------------------------------
# 文本摘要
# ---------------------------------------------------------------------------

def fund_summary(fund_code: str, benchmark_code: Optional[str] = None) -> str:
    """
    生成基金的简要文本摘要。

    参数:
        fund_code: 基金代码
        benchmark_code: 基准基金代码 (可选)

    返回:
        str: 格式化的文本摘要
    """
    info = fetcher.get_fund_info(fund_code)
    nav_df = fetcher.get_fund_nav(fund_code)

    lines = []
    lines.append("=" * 60)
    lines.append(f"【基金摘要】{info.get('name', '')} ({fund_code})")
    lines.append("=" * 60)

    lines.append(f"  类型: {info.get('type', 'N/A')}")
    lines.append(f"  管理人: {info.get('manager_company', 'N/A')}")
    lines.append(f"  成立日期: {info.get('inception_date', 'N/A')}")
    lines.append(f"  最新规模: {info.get('latest_size', 'N/A')}")

    # 近期收益
    period_returns = fetcher.get_fund_returns(fund_code)
    if period_returns:
        lines.append(f"\n  --- 区间收益 ---")
        label_map = {
            "1m": "近1月", "3m": "近3月", "6m": "近6月",
            "1y": "近1年", "3y": "近3年", "ytd": "今年来",
        }
        for k, label in label_map.items():
            if k in period_returns:
                lines.append(f"  {label}: {period_returns[k] * 100:6.2f}%")

    # 基础指标
    if not nav_df.empty and "nav" in nav_df.columns:
        nav = nav_df["nav"]
        ret = nav.pct_change().dropna()
        ann_ret = analyzer.annualized_return(nav)
        vol = analyzer.annualized_volatility(ret)
        md = analyzer.max_drawdown(nav)
        sr = analyzer.sharpe_ratio(ret)

        lines.append(f"\n  --- 核心指标 ---")
        lines.append(f"  年化收益: {ann_ret * 100:.2f}%" if not np.isnan(ann_ret) else "N/A")
        lines.append(f"  年化波动: {vol * 100:.2f}%")
        lines.append(f"  最大回撤: {md * 100:.2f}%")
        lines.append(f"  夏普比率: {sr:.4f}" if not np.isnan(sr) else "N/A")

    # 基准对比
    if benchmark_code:
        bench_nav_df = fetcher.get_fund_nav(benchmark_code)
        if not bench_nav_df.empty and "nav" in bench_nav_df.columns:
            bench_nav = bench_nav_df["nav"]
            bench_ret = bench_nav.pct_change().dropna()
            fund_ret = nav_df["nav"].pct_change().dropna()

            alpha, beta = analyzer.alpha_beta(fund_ret, bench_ret)
            ir = analyzer.information_ratio(fund_ret, bench_ret)
            lines.append(f"\n  --- 基准对比 ---")
            lines.append(f"  Alpha: {alpha * 100:.4f}%")
            lines.append(f"  Beta: {beta:.4f}")
            lines.append(f"  信息比率: {ir:.4f}")

    # 前十大持仓
    holdings = fetcher.get_fund_holdings(fund_code)
    if holdings:
        lines.append(f"\n  --- 前十大持仓 ---")
        for i, h in enumerate(holdings[:10], 1):
            if "stock_name" in h:
                ratio_str = f"{h['ratio'] * 100:.2f}%" if "ratio" in h and h['ratio'] else "N/A"
                lines.append(f"  {i:2d}. {h['stock_name']} ({h.get('stock_code', '')}) - {ratio_str}")

    lines.append("=" * 60)
    return "\n".join(lines)


def fund_comparison(fund_codes: list, benchmark_code: Optional[str] = None) -> str:
    """
    对比多只基金的指标，生成表格。

    参数:
        fund_codes: 基金代码列表
        benchmark_code: 基准代码 (可选)

    返回:
        str: 格式化的对比表格
    """
    rows = []

    for code in fund_codes:
        info = fetcher.get_fund_info(code)
        nav_df = fetcher.get_fund_nav(code)
        card = analyzer.fund_report_card(code)

        name = card.get("基金名称", info.get("name", code))
        ann_ret = card.get("年化收益率", "N/A")
        vol = card.get("年化波动率", "N/A")
        md = card.get("最大回撤", "N/A")
        sharpe = card.get("夏普比率", "N/A")
        sortino = card.get("索提诺比率", "N/A")
        win = card.get("胜率", "N/A")
        var95 = card.get("VaR (95%, 历史)", "N/A")
        consec = card.get("最大连续亏损天数", "N/A")

        rows.append({
            "代码": code,
            "名称": name[:20] if len(name) > 20 else name,
            "年化收益%": ann_ret,
            "年化波动%": vol,
            "最大回撤%": md,
            "夏普比率": sharpe,
            "索提诺比率": sortino,
            "胜率%": win,
            "VaR95%": var95,
            "连续亏损": consec,
        })

    if not rows:
        return "没有找到可对比的数据。"

    df = pd.DataFrame(rows)

    # 格式化数值
    for col in ["年化收益%", "年化波动%", "最大回撤%", "胜率%", "VaR95%"]:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: f"{x:.2f}" if isinstance(x, (int, float)) else str(x))
    for col in ["夏普比率", "索提诺比率"]:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: f"{x:.4f}" if isinstance(x, (int, float)) else str(x))

    return df.to_string(index=False)


# ---------------------------------------------------------------------------
# CSV 导出
# ---------------------------------------------------------------------------

def export_to_csv(fund_code: str, filename: Optional[str] = None) -> str:
    """
    将基金净值数据导出为 CSV。

    参数:
        fund_code: 基金代码
        filename: 输出文件名，默认 data/csv/{code}_nav.csv

    返回:
        str: 保存的 CSV 文件路径
    """
    nav_df = fetcher.get_fund_nav(fund_code)
    if nav_df.empty:
        raise ValueError(f"基金 {fund_code} 没有净值数据")

    if filename is None:
        out_dir = os.path.join(os.path.dirname(__file__), "..", "data", "csv")
        os.makedirs(out_dir, exist_ok=True)
        filename = os.path.join(out_dir, f"{fund_code}_nav.csv")

    nav_df.to_csv(filename, index=False, encoding="utf-8-sig")
    print(f"[Reporter] 已导出 {len(nav_df)} 条记录 -> {filename}")
    return filename


# ---------------------------------------------------------------------------
# Markdown 报告
# ---------------------------------------------------------------------------

def generate_report(fund_code: str, benchmark_code: Optional[str] = None) -> str:
    """
    生成基金的完整 Markdown 分析报告。

    参数:
        fund_code: 基金代码
        benchmark_code: 基准基金代码 (可选)

    返回:
        str: Markdown 报告内容
    """
    info = fetcher.get_fund_info(fund_code)
    nav_df = fetcher.get_fund_nav(fund_code)
    card = analyzer.fund_report_card(fund_code)
    holdings = fetcher.get_fund_holdings(fund_code)
    manager = fetcher.get_fund_manager(fund_code)

    md_lines = []
    md_lines.append(f"# 基金分析报告: {card.get('基金名称', '')} ({fund_code})")
    md_lines.append(f"")
    md_lines.append(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    md_lines.append(f"> 数据区间: {card.get('分析区间', 'N/A')}")
    md_lines.append(f"")

    # 基本信息
    md_lines.append(f"## 基本信息")
    md_lines.append(f"")
    md_lines.append(f"| 项目 | 内容 |")
    md_lines.append(f"|------|------|")
    md_lines.append(f"| 基金代码 | {fund_code} |")
    md_lines.append(f"| 基金名称 | {info.get('name', 'N/A')} |")
    md_lines.append(f"| 基金类型 | {info.get('type', 'N/A')} |")
    md_lines.append(f"| 管理人 | {info.get('manager_company', 'N/A')} |")
    md_lines.append(f"| 托管人 | {info.get('custodian', 'N/A')} |")
    md_lines.append(f"| 成立日期 | {info.get('inception_date', 'N/A')} |")
    md_lines.append(f"| 最新规模 | {info.get('latest_size', 'N/A')} |")
    if manager:
        md_lines.append(f"| 基金经理 | {manager.get('manager_name', 'N/A')} |")
        md_lines.append(f"| 任职日期 | {manager.get('tenure_start', 'N/A')} |")
    md_lines.append(f"")

    # 业绩指标
    md_lines.append(f"## 业绩指标")
    md_lines.append(f"")
    md_lines.append(f"| 指标 | 数值 |")
    md_lines.append(f"|------|------|")

    perf_keys = [
        "年化收益率", "年化波动率", "最大回撤", "胜率", "盈亏比",
        "夏普比率", "索提诺比率", "卡尔玛比率",
        "VaR (95%, 历史)", "CVaR (95%)", "最大连续亏损天数",
        "Alpha", "Beta", "信息比率", "跟踪误差",
    ]
    for key in perf_keys:
        val = card.get(key)
        if val is not None and val != "":
            unit = "%" if key in ("年化收益率", "年化波动率", "最大回撤", "胜率", "VaR (95%, 历史)", "CVaR (95%)", "跟踪误差") else ""
            md_lines.append(f"| {key} | {val}{unit} |")
    md_lines.append(f"")

    # 区间收益
    period_returns = fetcher.get_fund_returns(fund_code)
    if period_returns:
        md_lines.append(f"## 区间收益")
        md_lines.append(f"")
        md_lines.append(f"| 区间 | 收益率 |")
        md_lines.append(f"|------|--------|")
        label_map = {
            "1w": "近1周", "1m": "近1月", "3m": "近3月", "6m": "近6月",
            "1y": "近1年", "2y": "近2年", "3y": "近3年",
            "ytd": "今年来", "since_inception": "成立来",
        }
        for k, label in label_map.items():
            val = period_returns.get(k)
            if val is not None:
                md_lines.append(f"| {label} | {val * 100:.2f}% |")
        md_lines.append(f"")

    # 持仓分析
    if holdings:
        md_lines.append(f"## 前十大持仓")
        md_lines.append(f"")
        md_lines.append(f"| # | 股票名称 | 代码 | 占净值比例 |")
        md_lines.append(f"|---|----------|------|------------|")
        count = 0
        for h in holdings:
            if "stock_name" in h:
                count += 1
                ratio = f"{h['ratio'] * 100:.2f}%" if "ratio" in h and h['ratio'] else "N/A"
                md_lines.append(f"| {count} | {h['stock_name']} | {h.get('stock_code', '')} | {ratio} |")
                if count >= 10:
                    break

        # 行业分布
        industry_section = [h for h in holdings if "__industry_breakdown" in h]
        if industry_section:
            md_lines.append(f"")
            md_lines.append(f"### 行业分布")
            md_lines.append(f"")
            md_lines.append(f"| 行业 | 占比 |")
            md_lines.append(f"|------|------|")
            for ind in industry_section[0]["__industry_breakdown"]:
                ratio = f"{ind['industry_ratio'] * 100:.2f}%" if "industry_ratio" in ind else "N/A"
                md_lines.append(f"| {ind.get('industry_name', '')} | {ratio} |")
        md_lines.append(f"")

    # 评级
    rating = fetcher.get_fund_rating(fund_code)
    if rating:
        md_lines.append(f"## 基金评级")
        md_lines.append(f"")
        for k, v in rating.items():
            stars = "★" * int(v) + "☆" * (5 - int(v)) if isinstance(v, int) else str(v)
            md_lines.append(f"- **{k}**: {stars}")
        md_lines.append(f"")

    # 风险提示
    md_lines.append(f"## 风险提示")
    md_lines.append(f"")
    md_lines.append(f"- 本报告仅供参考，不构成投资建议。")
    md_lines.append(f"- 过往业绩不代表未来表现。")
    md_lines.append(f"- 基金投资有风险，投资需谨慎。")
    md_lines.append(f"- 数据来源: 天天基金 (akshare 接口)")
    md_lines.append(f"")

    return "\n".join(md_lines)


import numpy as np
