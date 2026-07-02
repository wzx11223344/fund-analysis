"""
投资组合优化模块
==============
基于均值-方差框架的资产配置工具，支持多种优化目标。

功能:
    - 均值-方差优化 (Markowitz 有效前沿)
    - 全局最小方差组合
    - 最大夏普比率组合 (切线组合)
    - 风险平价组合
    - Black-Litterman 模型
    - 蒙特卡洛模拟
"""

import warnings
from typing import Optional, Tuple

import numpy as np
import pandas as pd
from scipy import optimize

warnings.filterwarnings("ignore", category=RuntimeWarning)


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _check_returns(returns: pd.DataFrame) -> pd.DataFrame:
    """检查并清理收益率矩阵."""
    returns = returns.dropna(how="any")
    if returns.empty or returns.shape[1] < 2:
        raise ValueError("需要至少 2 个资产且数据非空")
    return returns


def portfolio_performance(weights: np.ndarray,
                           returns: pd.DataFrame,
                           periods_per_year: int = 252) -> Tuple[float, float, float]:
    """
    计算投资组合的收益、波动率和夏普比率。

    参数:
        weights: 权重向量 (和为 1)
        returns: 各资产的收益率 DataFrame
        periods_per_year: 年化期数

    返回:
        (port_return, port_vol, port_sharpe)
    """
    ann_returns = returns.mean() * periods_per_year
    cov = returns.cov() * periods_per_year

    port_return = np.dot(weights, ann_returns)
    port_vol = np.sqrt(np.dot(weights.T, np.dot(cov, weights)))
    sharpe = port_return / port_vol if port_vol > 0 else np.nan

    return float(port_return), float(port_vol), float(sharpe)


# ---------------------------------------------------------------------------
# 均值-方差优化
# ---------------------------------------------------------------------------

def mean_variance_optimization(returns: pd.DataFrame,
                                risk_free: float = 0.02,
                                periods_per_year: int = 252,
                                n_points: int = 50) -> dict:
    """
    Markowitz 有效前沿 — 生成一系列最优组合。

    参数:
        returns: 各资产的收益率 DataFrame
        risk_free: 年化无风险利率
        periods_per_year: 年化期数
        n_points: 有效前沿上的点数

    返回:
        dict: {
            "frontier": [(ret, vol, sharpe), ...],
            "min_vol": {"return": ..., "vol": ..., "weights": {name: w, ...}},
            "max_sharpe": {"return": ..., "vol": ..., "weights": {name: w, ...}},
        }
    """
    returns = _check_returns(returns)
    n_assets = returns.shape[1]
    ann_returns = returns.mean() * periods_per_year
    cov = returns.cov() * periods_per_year
    names = returns.columns.tolist()

    # 约束: 权重和为 1
    constraints = ({"type": "eq", "fun": lambda w: np.sum(w) - 1},)
    bounds = tuple((0, 1) for _ in range(n_assets))  # 不允许做空

    def _portfolio_stats(weights):
        ret = np.dot(weights, ann_returns)
        vol = np.sqrt(np.dot(weights.T, np.dot(cov, weights)))
        sharpe = (ret - risk_free) / vol if vol > 0 else 0
        return ret, vol, sharpe

    # 最小化波动率
    def _min_vol(weights):
        return _portfolio_stats(weights)[1]

    # 最大化夏普
    def _neg_sharpe(weights):
        return -_portfolio_stats(weights)[2]

    # 寻找目标收益范围
    min_ret, max_ret = ann_returns.min(), ann_returns.max()
    target_returns = np.linspace(min_ret, max_ret, n_points)

    # 求解全局最小方差
    init_guess = np.array([1.0 / n_assets] * n_assets)
    min_vol_result = optimize.minimize(_min_vol, init_guess,
                                        method="SLSQP",
                                        bounds=bounds,
                                        constraints=constraints)
    min_vol_weights = min_vol_result.x

    # 求解最大夏普
    max_sharpe_result = optimize.minimize(_neg_sharpe, init_guess,
                                           method="SLSQP",
                                           bounds=bounds,
                                           constraints=constraints)
    max_sharpe_weights = max_sharpe_result.x

    # 有效前沿
    frontier = []
    for target in target_returns:
        # 修改约束: 增加目标收益
        cons = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1},
            {"type": "eq", "fun": lambda w, t=target: np.dot(w, ann_returns) - t},
        ]
        result = optimize.minimize(_min_vol, init_guess,
                                    method="SLSQP",
                                    bounds=bounds,
                                    constraints=cons)
        if result.success:
            w = result.x
            r, v, s = _portfolio_stats(w)
            frontier.append((r, v, s))

    return {
        "frontier": frontier,
        "min_vol": {
            "return": float(_portfolio_stats(min_vol_weights)[0]),
            "vol": float(_portfolio_stats(min_vol_weights)[1]),
            "sharpe": float(_portfolio_stats(min_vol_weights)[2]),
            "weights": {names[i]: round(float(min_vol_weights[i]), 4) for i in range(n_assets) if min_vol_weights[i] > 0.001},
        },
        "max_sharpe": {
            "return": float(_portfolio_stats(max_sharpe_weights)[0]),
            "vol": float(_portfolio_stats(max_sharpe_weights)[1]),
            "sharpe": float(_portfolio_stats(max_sharpe_weights)[2]),
            "weights": {names[i]: round(float(max_sharpe_weights[i]), 4) for i in range(n_assets) if max_sharpe_weights[i] > 0.001},
        },
    }


# ---------------------------------------------------------------------------
# 便捷函数
# ---------------------------------------------------------------------------

def min_variance_portfolio(returns: pd.DataFrame,
                           periods_per_year: int = 252) -> dict:
    """
    全局最小方差组合: 风险最低的资产配置。

    参数:
        returns: 各资产的收益率 DataFrame
        periods_per_year: 年化期数

    返回:
        dict: 包含收益率、波动率和权重
    """
    result = mean_variance_optimization(returns, n_points=2)
    return result["min_vol"]


def max_sharpe_portfolio(returns: pd.DataFrame,
                          risk_free: float = 0.02,
                          periods_per_year: int = 252) -> dict:
    """
    最大夏普比率组合 (切线组合): 每单位风险收益最高。

    参数:
        returns: 各资产的收益率 DataFrame
        risk_free: 年化无风险利率
        periods_per_year: 年化期数

    返回:
        dict: 包含收益率、波动率、夏普比率和权重
    """
    result = mean_variance_optimization(returns, risk_free, periods_per_year)
    return result["max_sharpe"]


# ---------------------------------------------------------------------------
# 风险平价
# ---------------------------------------------------------------------------

def risk_parity_portfolio(returns: pd.DataFrame,
                           periods_per_year: int = 252,
                           max_iter: int = 1000,
                           tolerance: float = 1e-7) -> dict:
    """
    风险平价组合: 各资产对组合总风险的贡献相等。

    使用牛顿法迭代求解。

    参数:
        returns: 各资产的收益率 DataFrame
        periods_per_year: 年化期数
        max_iter: 最大迭代次数
        tolerance: 收敛容差

    返回:
        dict: {"return": ..., "vol": ..., "weights": {name: w, ...}}
    """
    returns = _check_returns(returns)
    n_assets = returns.shape[1]
    cov = returns.cov() * periods_per_year
    ann_returns = returns.mean() * periods_per_year
    names = returns.columns.tolist()

    def _risk_contribution(w, cov):
        """计算各资产的风险贡献."""
        port_vol = np.sqrt(np.dot(w.T, np.dot(cov, w)))
        if port_vol == 0:
            return np.ones(n_assets) / n_assets
        # 边际风险贡献
        mrc = np.dot(cov, w) / port_vol
        # 总风险贡献
        rc = w * mrc
        return rc

    def _objective(w):
        rc = _risk_contribution(w, cov)
        target_rc = np.mean(rc)
        return np.sum((rc - target_rc) ** 2)

    constraints = ({"type": "eq", "fun": lambda w: np.sum(w) - 1},)
    bounds = tuple((0, 1) for _ in range(n_assets))
    init_guess = np.array([1.0 / n_assets] * n_assets)

    result = optimize.minimize(_objective, init_guess,
                                method="SLSQP",
                                bounds=bounds,
                                constraints=constraints,
                                options={"maxiter": max_iter, "ftol": tolerance})

    if not result.success:
        warnings.warn(f"风险平价优化未完全收敛: {result.message}")

    w = result.x
    port_ret = float(np.dot(w, ann_returns))
    port_vol = float(np.sqrt(np.dot(w.T, np.dot(cov, w))))

    return {
        "return": port_ret,
        "vol": port_vol,
        "sharpe": port_ret / port_vol if port_vol > 0 else np.nan,
        "weights": {names[i]: round(float(w[i]), 4) for i in range(n_assets) if w[i] > 0.001},
    }


# ---------------------------------------------------------------------------
# Black-Litterman 模型
# ---------------------------------------------------------------------------

def black_litterman(returns: pd.DataFrame,
                    views: dict,
                    market_caps: Optional[dict] = None,
                    tau: float = 0.05,
                    delta: float = 2.5,
                    periods_per_year: int = 252) -> dict:
    """
    Black-Litterman 资产配置模型。

    结合市场均衡收益与投资者主观观点，生成后验收益分布。

    参数:
        returns: 各资产的收益率 DataFrame
        views: 观点字典，格式:
            {"绝对观点": {"资产名": 预期收益, ...},
             "相对观点": [("资产A", "资产B", 优劣程度), ...]}
        market_caps: 市场市值权重 (dict, {name: market_cap})
        tau: 观点不确定性标量 (默认 0.05)
        delta: 风险厌恶系数 (默认 2.5)
        periods_per_year: 年化期数

    返回:
        dict: 包含后验收益、后验协方差、最优权重
    """
    returns = _check_returns(returns)
    n_assets = returns.shape[1]
    names = returns.columns.tolist()
    cov = returns.cov() * periods_per_year

    # 市场权重
    if market_caps is None:
        market_weights = np.array([1.0 / n_assets] * n_assets)
    else:
        caps = np.array([market_caps.get(name, 1.0) for name in names])
        market_weights = caps / caps.sum()

    # 均衡收益 (逆优化)
    pi = delta * np.dot(cov, market_weights)

    # 构建观点矩阵 P 和 Q
    n_views = 0
    absolute_views = views.get("绝对观点", {})
    relative_views = views.get("相对观点", [])

    # 先统计观点数
    if absolute_views:
        n_views += len(absolute_views)
    if relative_views:
        n_views += len(relative_views)

    if n_views == 0:
        # 无观点 => 返回市场组合
        return {
            "posterior_returns": {names[i]: float(pi[i]) for i in range(n_assets)},
            "posterior_cov": cov,
            "optimal_weights": {names[i]: float(market_weights[i]) for i in range(n_assets)},
            "implied_returns": {names[i]: float(pi[i]) for i in range(n_assets)},
        }

    P = np.zeros((n_views, n_assets))
    Q = np.zeros(n_views)
    idx = 0

    # 绝对观点: P 矩阵中对应位置为 1
    for asset, ret in absolute_views.items():
        if asset in names:
            P[idx, names.index(asset)] = 1.0
            Q[idx] = ret
            idx += 1

    # 相对观点: e.g. 资产A 比 资产B 好 x%
    for asset_a, asset_b, magnitude in relative_views:
        if asset_a in names and asset_b in names:
            P[idx, names.index(asset_a)] = 1.0
            P[idx, names.index(asset_b)] = -1.0
            Q[idx] = magnitude
            idx += 1

    # 观点不确定性
    omega = np.diag(np.diag(tau * np.dot(P, np.dot(cov, P.T))))

    # 后验收益
    cov_pi = tau * cov
    temp = np.linalg.inv(np.linalg.inv(cov_pi) + np.dot(P.T, np.dot(np.linalg.inv(omega), P)))
    posterior_mean = np.dot(temp, np.dot(np.linalg.inv(cov_pi), pi) + np.dot(P.T, np.dot(np.linalg.inv(omega), Q)))
    posterior_cov = cov + temp

    # 后验最优权重
    optimal_weights = np.dot(np.linalg.inv(delta * posterior_cov), posterior_mean)
    # 不允许做空
    optimal_weights = np.maximum(optimal_weights, 0)
    optimal_weights = optimal_weights / optimal_weights.sum() if optimal_weights.sum() > 0 else optimal_weights

    return {
        "posterior_returns": {names[i]: float(posterior_mean[i]) for i in range(n_assets)},
        "posterior_cov": posterior_cov,
        "optimal_weights": {names[i]: round(float(optimal_weights[i]), 4) for i in range(n_assets) if optimal_weights[i] > 0.001},
        "implied_returns": {names[i]: float(pi[i]) for i in range(n_assets)},
    }


# ---------------------------------------------------------------------------
# 蒙特卡洛模拟
# ---------------------------------------------------------------------------

def monte_carlo_simulation(returns: pd.DataFrame,
                            n_portfolios: int = 5000,
                            periods_per_year: int = 252) -> dict:
    """
    蒙特卡洛模拟 — 生成大量随机组合并计算其收益/风险。

    参数:
        returns: 各资产的收益率 DataFrame
        n_portfolios: 模拟的组合数量
        periods_per_year: 年化期数

    返回:
        dict: {
            "simulations": [{"return": ..., "vol": ..., "sharpe": ...}, ...],
            "best_sharpe": {"return": ..., "vol": ..., "sharpe": ..., "weights": {...}},
            "min_vol": {"return": ..., "vol": ..., "sharpe": ..., "weights": {...}},
        }
    """
    returns = _check_returns(returns)
    n_assets = returns.shape[1]
    ann_returns = returns.mean() * periods_per_year
    cov = returns.cov() * periods_per_year
    names = returns.columns.tolist()

    results = []
    all_weights = []

    for _ in range(n_portfolios):
        # 生成随机权重 (Dirichlet 分布)
        w = np.random.dirichlet(np.ones(n_assets))
        all_weights.append(w)

        port_ret = np.dot(w, ann_returns)
        port_vol = np.sqrt(np.dot(w.T, np.dot(cov, w)))
        sharpe = port_ret / port_vol if port_vol > 0 else 0

        results.append((port_ret, port_vol, sharpe))

    results = np.array(results)
    all_weights = np.array(all_weights)

    # 最佳夏普
    best_idx = np.argmax(results[:, 2])
    best_weights = {names[i]: round(float(all_weights[best_idx, i]), 4)
                    for i in range(n_assets) if all_weights[best_idx, i] > 0.001}

    # 最小波动
    min_vol_idx = np.argmin(results[:, 1])
    min_vol_weights = {names[i]: round(float(all_weights[min_vol_idx, i]), 4)
                       for i in range(n_assets) if all_weights[min_vol_idx, i] > 0.001}

    simulations = [
        {"return": float(r[0]), "vol": float(r[1]), "sharpe": float(r[2])}
        for r in results
    ]

    return {
        "simulations": simulations,
        "best_sharpe": {
            "return": float(results[best_idx, 0]),
            "vol": float(results[best_idx, 1]),
            "sharpe": float(results[best_idx, 2]),
            "weights": best_weights,
        },
        "min_vol": {
            "return": float(results[min_vol_idx, 0]),
            "vol": float(results[min_vol_idx, 1]),
            "sharpe": float(results[min_vol_idx, 2]),
            "weights": min_vol_weights,
        },
    }
