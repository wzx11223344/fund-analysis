#!/usr/bin/env python3
"""
FundAnalyzer CLI — 公募基金智能分析命令行工具
=============================================
用法:
    python fund_cli.py search <keyword>         搜索基金
    python fund_cli.py info <code>              基金基本信息
    python fund_cli.py analyze <code>           全面分析
    python fund_cli.py compare <code1> <code2>  对比两只基金
    python fund_cli.py optimize <c1> <c2> <c3>  组合优化 (3只)
    python fund_cli.py report <code>            生成 Markdown 报告
    python fund_cli.py export <code>            导出净值 CSV
    python fund_cli.py clearcache               清空缓存
"""

import argparse
import sys
import os

# 确保能找到 fund_analyzer 包
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fund_analyzer import fetcher, analyzer, portfolio, reporter


def cmd_search(args):
    """搜索基金."""
    results = fetcher.search_fund(args.keyword)
    if not results:
        print(f"未找到匹配 '{args.keyword}' 的基金。")
        return

    print(f"\n找到 {len(results)} 只基金 (前 {min(20, len(results))} 条):\n")
    print(f"{'代码':<8} {'名称':<30} {'类型':<12} {'净值':<10} {'日涨跌':<10}")
    print("-" * 70)
    for r in results[:20]:
        code = r.get("code", r.get("基金代码", ""))
        name = r.get("name", r.get("基金简称", ""))[:28]
        ftype = r.get("type", r.get("基金类型", ""))[:10]
        nav = r.get("nav", r.get("单位净值", ""))
        dret = r.get("daily_return", r.get("日增长率", ""))
        print(f"{code:<8} {name:<30} {ftype:<12} {str(nav):<10} {str(dret):<10}")


def cmd_info(args):
    """显示基金基本信息."""
    info = fetcher.get_fund_info(args.code)
    if not info or not info.get("name"):
        print(f"无法获取基金 {args.code} 的信息。")
        return

    print(f"\n{'='*50}")
    print(f"  基金代码: {info.get('code', args.code)}")
    print(f"  基金名称: {info.get('name', 'N/A')}")
    print(f"  基金类型: {info.get('type', 'N/A')}")
    print(f"  管理人: {info.get('manager_company', 'N/A')}")
    print(f"  托管人: {info.get('custodian', 'N/A')}")
    print(f"  成立日期: {info.get('inception_date', 'N/A')}")
    print(f"  最新规模: {info.get('latest_size', 'N/A')}")
    print(f"  管理费: {info.get('management_fee', 'N/A')}")
    print(f"  托管费: {info.get('custody_fee', 'N/A')}")
    print(f"  {'='*50}")

    # 基金经理
    mgr = fetcher.get_fund_manager(args.code)
    if mgr and mgr.get("manager_name"):
        print(f"\n  基金经理: {mgr['manager_name']}")
        print(f"  任职起始: {mgr.get('tenure_start', 'N/A')}")

    # 评级
    rating = fetcher.get_fund_rating(args.code)
    if rating:
        print(f"\n  基金评级:")
        for k, v in rating.items():
            print(f"    {k}: {v}")


def cmd_analyze(args):
    """全面分析基金."""
    print(f"\n正在分析基金 {args.code} ...\n")

    # 基本信息
    info = fetcher.get_fund_info(args.code)
    name = info.get("name", args.code)
    print(f"基金: {name} ({args.code})\n")

    # 获取指标卡片
    card = analyzer.fund_report_card(args.code)
    if "error" in card:
        print(f"错误: {card['error']}")
        return

    print(f"{'指标':<24} {'数值':<12}")
    print("-" * 36)
    for key in [
        "分析区间", "数据天数", "年化收益率", "年化波动率",
        "最大回撤", "胜率", "盈亏比", "夏普比率", "索提诺比率",
        "卡尔玛比率", "VaR (95%, 历史)", "CVaR (95%)", "最大连续亏损天数",
    ]:
        val = card.get(key, "")
        if val != "" and val is not None:
            unit = "%" if key in ("年化收益率", "年化波动率", "最大回撤", "胜率",
                                   "VaR (95%, 历史)", "CVaR (95%)") else ""
            print(f"{key:<24} {val}{unit:<12}")

    # 区间收益
    period_returns = fetcher.get_fund_returns(args.code)
    if period_returns:
        print(f"\n{'区间收益':<24}")
        print("-" * 36)
        label_map = {
            "1w": "近1周", "1m": "近1月", "3m": "近3月", "6m": "近6月",
            "1y": "近1年", "3y": "近3年", "ytd": "今年来",
        }
        for k, label in label_map.items():
            if k in period_returns:
                print(f"{label:<24} {period_returns[k] * 100:6.2f}%")

    # 前十大持仓
    holdings = fetcher.get_fund_holdings(args.code)
    if holdings:
        print(f"\n{'前十大持仓':<24}")
        print("-" * 50)
        for i, h in enumerate(holdings[:10], 1):
            if "stock_name" in h:
                ratio = f"{h['ratio'] * 100:.2f}%" if h.get("ratio") else "N/A"
                print(f"  {i:2d}. {h['stock_name']} ({h.get('stock_code','')}) - {ratio}")


def cmd_compare(args):
    """对比两只基金."""
    codes = [args.code1, args.code2]
    print(f"\n基金对比: {codes[0]} vs {codes[1]}\n")
    print(reporter.fund_comparison(codes))
    print()


def cmd_optimize(args):
    """组合优化."""
    codes = [args.code1, args.code2, args.code3]
    print(f"\n组合优化: {', '.join(codes)}\n")

    # 获取各基金的收益率序列
    returns_dict = {}
    for code in codes:
        nav_df = fetcher.get_fund_nav(code)
        if nav_df.empty or "nav" not in nav_df.columns:
            print(f"警告: 无法获取 {code} 的净值数据，跳过")
            continue
        info = fetcher.get_fund_info(code)
        name = info.get("name", code)[:12]
        # 使用收益率序列
        ret = nav_df["nav"].pct_change().dropna()
        returns_dict[name] = ret

    if len(returns_dict) < 2:
        print("错误: 至少需要 2 只有效基金的数据。")
        return

    returns_df = pd.DataFrame(returns_dict)

    # 蒙特卡洛模拟
    print("运行蒙特卡洛模拟 (5000 次)...")
    mc_result = portfolio.monte_carlo_simulation(returns_df, n_portfolios=5000)
    print(f"\n最优组合 (最大夏普):")
    print(f"  年化收益: {mc_result['best_sharpe']['return'] * 100:.2f}%")
    print(f"  年化波动: {mc_result['best_sharpe']['vol'] * 100:.2f}%")
    print(f"  夏普比率: {mc_result['best_sharpe']['sharpe']:.4f}")
    print(f"  权重: {mc_result['best_sharpe']['weights']}")

    print(f"\n最稳健组合 (最小波动):")
    print(f"  年化收益: {mc_result['min_vol']['return'] * 100:.2f}%")
    print(f"  年化波动: {mc_result['min_vol']['vol'] * 100:.2f}%")
    print(f"  夏普比率: {mc_result['min_vol']['sharpe']:.4f}")
    print(f"  权重: {mc_result['min_vol']['weights']}")

    # 最大夏普 (二次优化)
    print(f"\n解析优化 (最大夏普):")
    max_sr = portfolio.max_sharpe_portfolio(returns_df)
    print(f"  年化收益: {max_sr['return'] * 100:.2f}%")
    print(f"  年化波动: {max_sr['vol'] * 100:.2f}%")
    print(f"  夏普比率: {max_sr['sharpe']:.4f}")
    print(f"  权重: {max_sr['weights']}")

    # 风险平价
    print(f"\n风险平价组合:")
    rp = portfolio.risk_parity_portfolio(returns_df)
    print(f"  年化收益: {rp['return'] * 100:.2f}%")
    print(f"  年化波动: {rp['vol'] * 100:.2f}%")
    print(f"  夏普比率: {rp['sharpe']:.4f}")
    print(f"  权重: {rp['weights']}")


def cmd_report(args):
    """生成 Markdown 报告."""
    print(f"生成基金分析报告: {args.code}")
    md = reporter.generate_report(args.code)
    out_dir = os.path.join("data", "reports")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{args.code}_report.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"报告已保存: {out_path}")
    print(md)


def cmd_export(args):
    """导出净值 CSV."""
    path = reporter.export_to_csv(args.code)
    print(f"已导出: {path}")


def cmd_clearcache(args):
    """清空缓存."""
    fetcher.clear_cache()


def main():
    parser = argparse.ArgumentParser(
        description="FundAnalyzer — 公募基金智能分析工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python fund_cli.py search 沪深300
  python fund_cli.py info 110020
  python fund_cli.py analyze 110020
  python fund_cli.py compare 110020 000311
  python fund_cli.py optimize 110020 000311 005827
  python fund_cli.py report 110020
  python fund_cli.py export 110020
  python fund_cli.py clearcache
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # search
    p_search = subparsers.add_parser("search", help="搜索基金")
    p_search.add_argument("keyword", type=str, help="基金名称或代码关键词")

    # info
    p_info = subparsers.add_parser("info", help="基金基本信息")
    p_info.add_argument("code", type=str, help="基金代码 (如 110020)")

    # analyze
    p_analyze = subparsers.add_parser("analyze", help="全面分析基金")
    p_analyze.add_argument("code", type=str, help="基金代码")

    # compare
    p_compare = subparsers.add_parser("compare", help="对比两只基金")
    p_compare.add_argument("code1", type=str, help="基金代码1")
    p_compare.add_argument("code2", type=str, help="基金代码2")

    # optimize
    p_optimize = subparsers.add_parser("optimize", help="组合优化 (3只基金)")
    p_optimize.add_argument("code1", type=str, help="基金代码1")
    p_optimize.add_argument("code2", type=str, help="基金代码2")
    p_optimize.add_argument("code3", type=str, help="基金代码3")

    # report
    p_report = subparsers.add_parser("report", help="生成 Markdown 报告")
    p_report.add_argument("code", type=str, help="基金代码")

    # export
    p_export = subparsers.add_parser("export", help="导出净值 CSV")
    p_export.add_argument("code", type=str, help="基金代码")

    # clearcache
    subparsers.add_parser("clearcache", help="清空数据缓存")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # 命令路由
    cmd_map = {
        "search": cmd_search,
        "info": cmd_info,
        "analyze": cmd_analyze,
        "compare": cmd_compare,
        "optimize": cmd_optimize,
        "report": cmd_report,
        "export": cmd_export,
        "clearcache": cmd_clearcache,
    }

    # 确保 optimize 命令有 pandas
    if args.command == "optimize":
        import pandas as pd

    cmd_func = cmd_map[args.command]
    cmd_func(args)


if __name__ == "__main__":
    main()
