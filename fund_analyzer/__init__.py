"""
FundAnalyzer — 公募基金智能分析工具包
====================================
基于公开数据的公募基金全维度分析工具。
覆盖业绩归因、风险评估、持仓分析、组合优化。

模块:
    fetcher  — 数据获取 (基于 akshare)
    analyzer — 业绩指标与风险分析
    portfolio — 投资组合优化
    reporter — 报告生成
"""

from . import fetcher
from . import analyzer
from . import portfolio
from . import reporter

__version__ = "1.0.0"
__author__ = "FundAnalyzer"
__all__ = ["fetcher", "analyzer", "portfolio", "reporter"]
