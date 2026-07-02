"""
业绩指标与风险分析模块
====================
提供全面的基金业绩评价指标和风险度量，
涵盖收益、风险、风险调整后收益、回撤分析等。

指标清单:
    收益类:     annualized_return, win_rate, profit_factor
    风险类:     annualized_volatility, max_drawdown, var_*, conditional_var
    风险调整后: sharpe_ratio, sortino_ratio, calmar_ratio, information_ratio
    市场模型:   alpha_beta, tracking_error
    辅助:       consecutive_losses, fund_report_card
"""

import warnings
from typing import Optional, Union

import numpy as np
import pandas as pd

from . import fetcher

warnings.filterwarnings("ignore", category=RuntimeWarning)


# ---------------------------------------------------------------------------
# 收益类指标
# ---------------------------------------------------------------------------

def annualized_return(nav: pd.Series, periods_per_year: int = 252) -> float:
    """
    计算年化收益率 (CAGR)。

    参数:
        nav: 净值序列 (价格水平，非收益率)
        periods_per_year: 每年的期数，日频=252，周频=52，月频=12

    返回:
        float: 年化收益率 (如 0.12 表示 12%)
    """
    nav = nav.dropna()
    if len(nav) < 2:
        return np.nan
    total_return = nav.iloc[-1] / nav.iloc[0]
    n_years = len(nav) / periods_per_year
    if n_years <= 0:
        return np.nan
    return float(total_return ** (1.0 / n_years) - 1.0)


def _to_returns(nav: pd.Series) -> pd.Series:
    """净值序列 → 收益率序列."""
    return nav.dropna().pct_change().dropna()


def win_rate(returns: pd.Series) -> float:
    """
    胜率: 正收益率期数占比。

    参数:
        returns: 收益率序列

    返回:
        float: 0~1 之间的比率
    """
    returns = returns.dropna()
    if len(returns) == 0:
        return np.nan
    return float((returns > 0).sum() / len(returns))


def profit_factor(returns: pd.Series) -> float:
    """
    盈亏比: 总盈利 / 总亏损的绝对值。

    参数:
        returns: 收益率序列

    返回:
        float: >= 0
    """
    returns = returns.dropna()
    gross_profit = returns[returns > 0].sum()
    gross_loss = abs(returns[returns < 0].sum())
    if gross_loss == 0:
        return np.inf if gross_profit > 0 else np.nan
    return float(gross_profit / gross_loss)


# ---------------------------------------------------------------------------
# 风险类指标
# ---------------------------------------------------------------------------

def annualized_volatility(returns: pd.Series, periods_per_year: int = 252) -> float:
    """
    年化波动率。

    参数:
        returns: 收益率序列
        periods_per_year: 每年的期数

    返回:
        float: 年化标准差
    """
    returns = returns.dropna()
    if len(returns) < 2:
        return np.nan
    return float(returns.std() * np.sqrt(periods_per_year))


def max_drawdown(nav: pd.Series) -> float:
    """
    最大回撤: 峰值到谷底的最大跌幅。

    参数:
        nav: 净值序列

    返回:
        float: 正数表示最大回撤幅度 (如 0.25 表示 25%)
    """
    nav = nav.dropna()
    if len(nav) < 2:
        return np.nan
    cumulative_max = nav.cummax()
    drawdowns = (nav - cumulative_max) / cumulative_max
    return float(abs(drawdowns.min()))


def drawdown_series(nav: pd.Series) -> pd.Series:
    """
    回撤序列: 每个时间点的回撤幅度。

    参数:
        nav: 净值序列

    返回:
        pd.Series: 回撤序列 (正数)
    """
    nav = nav.dropna()
    cumulative_max = nav.cummax()
    return abs((nav - cumulative_max) / cumulative_max)


def consecutive_losses(returns: pd.Series) -> int:
    """
    最大连续亏损期数。

    参数:
        returns: 收益率序列

    返回:
        int: 最大连续亏损天数/期数
    """
    returns = returns.dropna()
    if len(returns) == 0:
        return 0
    is_negative = (returns < 0).astype(int)
    # 计算连续亏损
    streaks = is_negative.groupby((is_negative != is_negative.shift()).cumsum()).cumsum()
    return int(streaks.max()) if not streaks.empty else 0


# ---------------------------------------------------------------------------
# 风险调整后收益
# ---------------------------------------------------------------------------

def sharpe_ratio(returns: pd.Series, rf: float = 0.02, periods_per_year: int = 252) -> float:
    """
    夏普比率: (组合收益 - 无风险利率) / 波动率。
    衡量每单位总风险带来的超额收益。

    参数:
        returns: 收益率序列
        rf: 年化无风险利率 (如 0.02 = 2%)
        periods_per_year: 每年的期数

    返回:
        float: 年化夏普比率
    """
    returns = returns.dropna()
    if len(returns) < 2:
        return np.nan
    excess_returns = returns - rf / periods_per_year
    if excess_returns.std() == 0:
        return np.nan
    return float(np.sqrt(periods_per_year) * excess_returns.mean() / excess_returns.std())


def sortino_ratio(returns: pd.Series, rf: float = 0.02, periods_per_year: int = 252) -> float:
    """
    索提诺比率: 使用下行标准差代替总标准差。
    只惩罚下行风险。

    参数:
        returns: 收益率序列
        rf: 年化无风险利率
        periods_per_year: 每年的期数

    返回:
        float: 年化索提诺比率
    """
    returns = returns.dropna()
    if len(returns) < 2:
        return np.nan
    excess_returns = returns - rf / periods_per_year
    downside = returns[returns < 0]
    if len(downside) == 0:
        return np.inf if excess_returns.mean() > 0 else np.nan
    downside_std = np.sqrt((downside ** 2).sum() / len(returns))
    if downside_std == 0:
        return np.nan
    return float(np.sqrt(periods_per_year) * excess_returns.mean() / downside_std)


def calmar_ratio(returns: pd.Series, max_dd: Optional[float] = None, periods_per_year: int = 252) -> float:
    """
    卡尔玛比率: 年化收益率 / 最大回撤。
    衡量每单位最大回撤带来的年化收益。

    参数:
        returns: 收益率序列 (用于计算年化收益)
        max_dd: 最大回撤 (若已计算好可直接传入)
        periods_per_year: 每年的期数

    返回:
        float
    """
    ann_ret = annualized_return(_returns_to_nav(returns), periods_per_year) if max_dd is None else None
    if max_dd is None:
        nav = _returns_to_nav(returns)
        max_dd = max_drawdown(nav)
    if max_dd == 0 or np.isnan(max_dd):
        return np.nan
    if ann_ret is None:
        ann_ret = annualized_return(_returns_to_nav(returns), periods_per_year)
    return float(ann_ret / max_dd)


def information_ratio(fund_returns: pd.Series, benchmark_returns: pd.Series, periods_per_year: int = 252) -> float:
    """
    信息比率: (基金收益 - 基准收益) / 跟踪误差。
    衡量主动管理能力。

    参数:
        fund_returns: 基金收益率序列
        benchmark_returns: 基准收益率序列
        periods_per_year: 每年的期数

    返回:
        float
    """
    diff = fund_returns.dropna() - benchmark_returns.dropna()
    te = diff.std() * np.sqrt(periods_per_year)
    if te == 0:
        return np.nan
    excess_return = diff.mean() * periods_per_year
    return float(excess_return / te)


# ---------------------------------------------------------------------------
# 市场模型
# ---------------------------------------------------------------------------

def alpha_beta(fund_returns: pd.Series, benchmark_returns: pd.Series, rf: float = 0.02, periods_per_year: int = 252):
    """
    CAPM Alpha 和 Beta。

    参数:
        fund_returns: 基金收益率序列
        benchmark_returns: 基准收益率序列
        rf: 年化无风险利率
        periods_per_year: 每年的期数

    返回:
        (alpha, beta): (年化 Alpha, Beta)
    """
    fund = fund_returns.dropna()
    bench = benchmark_returns.dropna()
    # 对齐
    common = fund.index.intersection(bench.index)
    fund = fund.loc[common]
    bench = bench.loc[common]

    rf_period = rf / periods_per_year
    fund_excess = fund - rf_period
    bench_excess = bench - rf_period

    cov = np.cov(fund_excess, bench_excess)
    if cov[1, 1] == 0:
        return (np.nan, np.nan)
    beta = cov[0, 1] / cov[1, 1]
    alpha = (fund_excess.mean() - beta * bench_excess.mean()) * periods_per_year
    return (float(alpha), float(beta))


def tracking_error(fund_returns: pd.Series, benchmark_returns: pd.Series, periods_per_year: int = 252) -> float:
    """
    跟踪误差: 基金与基准收益率差异的年化标准差。

    参数:
        fund_returns: 基金收益率序列
        benchmark_returns: 基准收益率序列
        periods_per_year: 每年的期数

    返回:
        float
    """
    diff = fund_returns.dropna() - benchmark_returns.dropna()
    return float(diff.std() * np.sqrt(periods_per_year))


# ---------------------------------------------------------------------------
# 风险价值 (VaR)
# ---------------------------------------------------------------------------

def var_historical(returns: pd.Series, confidence: float = 0.95) -> float:
    """
    历史模拟法 VaR。

    参数:
        returns: 收益率序列
        confidence: 置信水平 (默认 95%)

    返回:
        float: VaR 值 (正数表示潜在最大损失比例)
    """
    returns = returns.dropna()
    if len(returns) == 0:
        return np.nan
    return float(abs(np.percentile(returns, (1 - confidence) * 100)))


def var_parametric(returns: pd.Series, confidence: float = 0.95) -> float:
    """
    参数法 VaR (假设正态分布)。

    参数:
        returns: 收益率序列
        confidence: 置信水平

    返回:
        float: VaR 值
    """
    from scipy import stats
    returns = returns.dropna()
    if len(returns) < 2:
        return np.nan
    mu = returns.mean()
    sigma = returns.std()
    z = stats.norm.ppf(1 - confidence)
    return float(abs(mu + z * sigma))


def conditional_var(returns: pd.Series, confidence: float = 0.95) -> float:
    """
    条件 VaR (Expected Shortfall): 超过 VaR 的尾部损失的期望值。

    参数:
        returns: 收益率序列
        confidence: 置信水平

    返回:
        float: CVaR
    """
    returns = returns.dropna()
    if len(returns) == 0:
        return np.nan
    threshold = np.percentile(returns, (1 - confidence) * 100)
    tail = returns[returns <= threshold]
    if len(tail) == 0:
        return float(abs(threshold))
    return float(abs(tail.mean()))


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _returns_to_nav(returns: pd.Series) -> pd.Series:
    """收益率序列 → 净值序列 (从 1 开始)."""
    return (1 + returns.dropna()).cumprod()


# ---------------------------------------------------------------------------
# 综合报告
# ---------------------------------------------------------------------------

def fund_report_card(fund_code: str, benchmark_returns: Optional[pd.Series] = None) -> dict:
    """
    生成基金指标卡片 — 一份包含核心业绩和风险指标的汇总字典。

    参数:
        fund_code: 基金代码
        benchmark_returns: 基准收益率序列 (可选，用于 Alpha/Beta/IR 计算)

    返回:
        dict: 包含各项指标的字典
    """
    # 获取净值
    nav_df = fetcher.get_fund_nav(fund_code)
    if nav_df.empty or "nav" not in nav_df.columns:
        return {"error": f"无法获取基金 {fund_code} 的净值数据"}

    nav = nav_df["nav"]
    returns = nav.pct_change().dropna()

    if "date" in nav_df.columns:
        nav_df["date"] = pd.to_datetime(nav_df["date"])
        start = nav_df["date"].iloc[0].strftime("%Y-%m-%d")
        end = nav_df["date"].iloc[-1].strftime("%Y-%m-%d")
    else:
        start, end = "", ""

    # 基础信息
    info = fetcher.get_fund_info(fund_code)
    md = max_drawdown(nav)

    card = {
        "基金代码": fund_code,
        "基金名称": info.get("name", ""),
        "基金类型": info.get("type", ""),
        "分析区间": f"{start} ~ {end}",
        "数据天数": len(nav),
    }

    # 收益
    card["年化收益率"] = round(annualized_return(nav) * 100, 2)
    card["年化波动率"] = round(annualized_volatility(returns) * 100, 2)
    card["胜率"] = round(win_rate(returns) * 100, 2)
    card["盈亏比"] = round(profit_factor(returns), 2)
    card["最大回撤"] = round(md * 100, 2)

    # 风险调整收益
    card["夏普比率"] = round(sharpe_ratio(returns), 4)
    card["索提诺比率"] = round(sortino_ratio(returns), 4)
    card["卡尔玛比率"] = round(calmar_ratio(returns, md), 4)

    # VaR
    card["VaR (95%, 历史)"] = round(var_historical(returns) * 100, 2)
    card["CVaR (95%)"] = round(conditional_var(returns) * 100, 2)

    # 最大连续亏损
    card["最大连续亏损天数"] = consecutive_losses(returns)

    # Alpha / Beta / IR (如有基准)
    if benchmark_returns is not None and len(benchmark_returns) > 0:
        alpha, beta = alpha_beta(returns, benchmark_returns)
        ir = information_ratio(returns, benchmark_returns)
        card["Alpha"] = round(alpha * 100, 4)
        card["Beta"] = round(beta, 4)
        card["信息比率"] = round(ir, 4)
        card["跟踪误差"] = round(tracking_error(returns, benchmark_returns) * 100, 4)

    # 收益率
    period_returns = fetcher.get_fund_returns(fund_code)
    for k, v in period_returns.items():
        card[f"收益_{k}"] = round(v * 100, 2)

    # 评级
    rating = fetcher.get_fund_rating(fund_code)
    for k, v in rating.items():
        card[k] = v

    return card
