#!/usr/bin/env python3
"""
FundAnalyzer 综合演示脚本
========================
展示基金分析工具的主要功能。

运行:
    python examples/demo.py
"""

import sys
import os

# 确保能找到 fund_analyzer 包
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fund_analyzer import fetcher, analyzer, portfolio, reporter


def print_separator(title):
    """打印分隔标题."""
    width = 65
    print("\n" + "=" * width)
    print(f"  {title}")
    print("=" * width)


def demo_search():
    """演示: 搜索基金."""
    print_separator("演示 1: 搜索基金")

    keywords = ["沪深300", "易方达", "中欧医疗"]
    for kw in keywords:
        print(f"\n搜索关键词: '{kw}'")
        results = fetcher.search_fund(kw)
        if results:
            print(f"  找到 {len(results)} 只基金")
            for r in results[:5]:
                code = r.get("code", r.get("基金代码", ""))
                name = r.get("name", r.get("基金简称", ""))
                ftype = r.get("type", r.get("基金类型", ""))
                print(f"    {code}  {name}  [{ftype}]")
        else:
            print("  无结果")


def demo_info():
    """演示: 基金基本信息."""
    print_separator("演示 2: 基金基本信息")

    # 易方达沪深300ETF联接A
    code = "110020"
    info = fetcher.get_fund_info(code)
    if info and info.get("name"):
        print(f"\n基金代码: {info.get('code', code)}")
        print(f"基金名称: {info.get('name', 'N/A')}")
        print(f"基金类型: {info.get('type', 'N/A')}")
        print(f"管理人: {info.get('manager_company', 'N/A')}")
        print(f"成立日期: {info.get('inception_date', 'N/A')}")
        print(f"最新规模: {info.get('latest_size', 'N/A')}")
        print(f"管理费: {info.get('management_fee', 'N/A')}")
    else:
        print(f"无法获取基金 {code} 的信息")


def demo_performance():
    """演示: 业绩分析."""
    print_separator("演示 3: 业绩指标计算")

    code = "110020"
    nav_df = fetcher.get_fund_nav(code)
    if nav_df.empty:
        print(f"无法获取 {code} 的净值数据")
        return

    nav = nav_df["nav"]
    returns = nav.pct_change().dropna()

    print(f"\n基金: {code} (易方达沪深300ETF联接A)")
    print(f"数据区间: {nav_df['date'].iloc[0]} ~ {nav_df['date'].iloc[-1]}")
    print(f"数据天数: {len(nav)}")

    # 计算各类指标
    ann_ret = analyzer.annualized_return(nav)
    ann_vol = analyzer.annualized_volatility(returns)
    md = analyzer.max_drawdown(nav)
    sr = analyzer.sharpe_ratio(returns)
    sortino = analyzer.sortino_ratio(returns)
    calmar = analyzer.calmar_ratio(returns, md)
    wr = analyzer.win_rate(returns)
    pf = analyzer.profit_factor(returns)
    var_h = analyzer.var_historical(returns)
    var_p = analyzer.var_parametric(returns)
    cvar = analyzer.conditional_var(returns)
    consec = analyzer.consecutive_losses(returns)

    print(f"\n{'指标':<24} {'数值':<12}")
    print("-" * 36)
    print(f"{'年化收益率 (CAGR)':<24} {ann_ret * 100:>6.2f}%")
    print(f"{'年化波动率':<24} {ann_vol * 100:>6.2f}%")
    print(f"{'最大回撤':<24} {md * 100:>6.2f}%")
    print(f"{'胜率':<24} {wr * 100:>6.2f}%")
    print(f"{'盈亏比':<24} {pf:>8.2f}")
    print(f"{'夏普比率':<24} {sr:>8.4f}")
    print(f"{'索提诺比率':<24} {sortino:>8.4f}")
    print(f"{'卡尔玛比率':<24} {calmar:>8.4f}")
    print(f"{'VaR (95%, 历史)':<24} {var_h * 100:>6.2f}%")
    print(f"{'VaR (95%, 参数)':<24} {var_p * 100:>6.2f}%")
    print(f"{'CVaR (95%)':<24} {cvar * 100:>6.2f}%")
    print(f"{'最大连续亏损':<24} {consec:>8d} 天")

    # 区间收益
    period_returns = fetcher.get_fund_returns(code)
    if period_returns:
        print(f"\n{'区间收益':<24}")
        print("-" * 36)
        label_map = {
            "1w": "近1周", "1m": "近1月", "3m": "近3月", "6m": "近6月",
            "1y": "近1年", "3y": "近3年", "ytd": "今年来",
        }
        for k, label in label_map.items():
            if k in period_returns:
                print(f"{label:<24} {period_returns[k] * 100:>6.2f}%")


def demo_report_card():
    """演示: 基金指标卡片."""
    print_separator("演示 4: 基金指标卡片")

    code = "110020"
    card = analyzer.fund_report_card(code)

    if "error" in card:
        print(f"错误: {card['error']}")
        return

    print(f"\n基金: {card.get('基金名称', code)} ({code})")
    print(f"分析区间: {card.get('分析区间', 'N/A')}")
    print(f"\n{'指标':<24} {'数值':<12}")
    print("-" * 36)
    for key in [
        "年化收益率", "年化波动率", "最大回撤", "胜率", "盈亏比",
        "夏普比率", "索提诺比率", "卡尔玛比率",
        "VaR (95%, 历史)", "CVaR (95%)", "最大连续亏损天数",
    ]:
        val = card.get(key, "")
        if val != "" and val is not None:
            unit = "%" if key in ("年化收益率", "年化波动率", "最大回撤", "胜率",
                                   "VaR (95%, 历史)", "CVaR (95%)") else ""
            print(f"{key:<24} {val}{unit}")


def demo_holdings():
    """演示: 持仓分析."""
    print_separator("演示 5: 持仓分析")

    # 分析一只主动管理型基金 (以易方达消费行业为例)
    code = "110022"  # 易方达消费行业股票
    holdings = fetcher.get_fund_holdings(code)
    info = fetcher.get_fund_info(code)

    print(f"\n基金: {info.get('name', code)} ({code})")

    if holdings:
        print(f"\n前十大持仓:")
        for i, h in enumerate(holdings[:10], 1):
            if "stock_name" in h:
                ratio = f"{h['ratio'] * 100:.2f}%" if h.get("ratio") else "N/A"
                print(f"  {i:2d}. {h['stock_name']} ({h.get('stock_code', '')}) - {ratio}")
    else:
        print("  无持仓数据")


def demo_portfolio():
    """演示: 组合优化."""
    print_separator("演示 6: 组合优化")

    # 三只不同风格的基金
    # 110020 - 易方达沪深300ETF联接A (大盘)
    # 110022 - 易方达消费行业股票 (消费)
    # 005827 - 易方达蓝筹精选 (混合)
    codes = ["110020", "110022", "005827"]

    print(f"构建组合的基金:")
    returns_dict = {}
    for code in codes:
        nav_df = fetcher.get_fund_nav(code)
        if nav_df.empty:
            print(f"  跳过 {code}: 无数据")
            continue
        info = fetcher.get_fund_info(code)
        name = info.get("name", code)[:15]
        ret = nav_df["nav"].pct_change().dropna()
        returns_dict[name] = ret
        print(f"  {code} - {name}")

    if len(returns_dict) < 2:
        print("至少需要 2 只有效基金。")
        return

    import pandas as pd
    returns_df = pd.DataFrame(returns_dict)

    # 蒙特卡洛模拟
    print(f"\n>> 蒙特卡洛模拟 (5000 次)...")
    mc = portfolio.monte_carlo_simulation(returns_df, n_portfolios=5000)
    print(f"  最优夏普组合:")
    for k, v in mc["best_sharpe"]["weights"].items():
        print(f"    {k}: {v * 100:.1f}%")
    print(f"    → 年化收益: {mc['best_sharpe']['return'] * 100:.2f}%")
    print(f"    → 年化波动: {mc['best_sharpe']['vol'] * 100:.2f}%")
    print(f"    → 夏普比率: {mc['best_sharpe']['sharpe']:.4f}")

    # 解析最大夏普
    print(f"\n>> Markowitz 最优 (最大夏普):")
    try:
        max_sr = portfolio.max_sharpe_portfolio(returns_df)
        print(f"  权重: {max_sr['weights']}")
        print(f"  → 年化收益: {max_sr['return'] * 100:.2f}%")
        print(f"  → 年化波动: {max_sr['vol'] * 100:.2f}%")
        print(f"  → 夏普比率: {max_sr['sharpe']:.4f}")
    except Exception as e:
        print(f"  优化失败: {e}")

    # 风险平价
    print(f"\n>> 风险平价组合:")
    try:
        rp = portfolio.risk_parity_portfolio(returns_df)
        print(f"  权重: {rp['weights']}")
        print(f"  → 年化收益: {rp['return'] * 100:.2f}%")
        print(f"  → 年化波动: {rp['vol'] * 100:.2f}%")
        print(f"  → 夏普比率: {rp['sharpe']:.4f}")
    except Exception as e:
        print(f"  计算失败: {e}")


def demo_report():
    """演示: 生成报告."""
    print_separator("演示 7: 生成 Markdown 报告")

    code = "110020"
    md = reporter.generate_report(code)

    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "reports")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{code}_demo_report.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(md)

    print(f"报告已生成: {out_path}")
    print(f"\n报告预览 (前 20 行):")
    print("-" * 50)
    for line in md.split("\n")[:20]:
        print(line)


def demo_export():
    """演示: 导出 CSV."""
    print_separator("演示 8: 导出净值 CSV")

    code = "110020"
    path = reporter.export_to_csv(code)
    print(f"已导出: {path}")


def main():
    print("\n" + "★" * 35)
    print("  FundAnalyzer 综合演示")
    print("  公募基金智能分析工具")
    print("★" * 35)

    try:
        demo_search()
        demo_info()
        demo_performance()
        demo_report_card()
        demo_holdings()
        demo_portfolio()
        demo_report()
        demo_export()
    except KeyboardInterrupt:
        print("\n演示被用户中断。")
    except Exception as e:
        print(f"\n演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

    print_separator("演示结束")
    print("感谢使用 FundAnalyzer!\n")


if __name__ == "__main__":
    main()
