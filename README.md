# FundAnalyzer — 公募基金智能分析工具

> 基于公开数据的公募基金全维度分析工具，覆盖业绩归因、风险评估、持仓分析、组合优化。

## 为什么做这个项目？

考取基金从业资格后，发现理论知识与实战之间存在鸿沟。市面上缺乏免费的、可编程的基金分析工具。于是决定用 Python 打通从数据获取到量化分析的完整链路。

## 功能特性

- **6000+ 公募基金数据** — 基于 akshare 免费获取天天基金数据
- **10+ 风险调整收益指标** — 夏普比率、索提诺比率、卡尔玛比率、信息比率
- **风险度量** — VaR (历史/参数法)、CVaR、最大回撤、连续亏损
- **CAPM 模型** — Alpha、Beta、跟踪误差
- **Markowitz 有效前沿** — 均值-方差优化、全局最小方差、最大夏普
- **风险平价** — 等风险贡献组合
- **Black-Litterman 模型** — 结合主观观点的资产配置
- **蒙特卡洛模拟** — 5000+ 随机组合可视化
- **一键报告** — Markdown 格式的全面分析报告

## 技术栈

| 模块 | 技术 |
|------|------|
| 数据获取 | akshare (免费，无需 API Key) |
| 数据分析 | pandas, numpy |
| 数值优化 | scipy.optimize |
| 可视化 | matplotlib (Notebook) |
| CLI | argparse |

## 快速开始

### 1. 安装

```bash
git clone <repo-url>
cd fund-analysis
pip install -r requirements.txt
```

### 2. CLI 使用

```bash
# 搜索基金
python fund_cli.py search 沪深300

# 基金基本信息
python fund_cli.py info 110020

# 全面分析
python fund_cli.py analyze 110020

# 对比两只基金
python fund_cli.py compare 110020 000311

# 组合优化 (三只基金)
python fund_cli.py optimize 110020 000311 005827

# 生成 Markdown 报告
python fund_cli.py report 110020

# 导出净值 CSV
python fund_cli.py export 110020

# 清空缓存
python fund_cli.py clearcache
```

### 3. Jupyter Notebook

```bash
jupyter notebook fund_analyzer.ipynb
```

### 4. Python 包方式

```python
from fund_analyzer import fetcher, analyzer, portfolio, reporter

# 搜索基金
results = fetcher.search_fund("易方达")

# 获取净值与指标
nav_df = fetcher.get_fund_nav("110020")
card = analyzer.fund_report_card("110020")

# 组合优化
returns = nav_df["nav"].pct_change().dropna()
result = portfolio.max_sharpe_portfolio(returns)

# 生成报告
reporter.generate_report("110020")
```

### 5. 演示脚本

```bash
python examples/demo.py
```

## 项目结构

```
fund-analysis/
├── README.md                          # 本文件
├── requirements.txt                   # 依赖
├── fund_analyzer.ipynb                # Jupyter Notebook 教程
├── fund_cli.py                        # 命令行工具
├── fund_analyzer/
│   ├── __init__.py                    # 包初始化
│   ├── fetcher.py                     # 数据获取 (akshare)
│   ├── analyzer.py                    # 业绩指标与风险分析
│   ├── portfolio.py                   # 投资组合优化
│   └── reporter.py                    # 报告生成
├── data/
│   ├── README.md                      # 数据目录说明
│   ├── cache/                         # 自动缓存
│   ├── csv/                           # 导出的 CSV
│   └── reports/                       # Markdown 报告
└── examples/
    └── demo.py                        # 综合演示
```

## 指标速览

| 指标 | 说明 |
|------|------|
| 年化收益率 (CAGR) | 几何平均年化收益率 |
| 年化波动率 | 收益率年化标准差 |
| 最大回撤 | 峰值到谷底的最大跌幅 |
| 夏普比率 | (收益 - 无风险) / 总风险 |
| 索提诺比率 | (收益 - 无风险) / 下行风险 |
| 卡尔玛比率 | 年化收益 / 最大回撤 |
| 信息比率 | 主动收益 / 跟踪误差 |
| Alpha | 超额收益 (CAPM) |
| Beta | 市场风险敞口 |
| VaR | 给定置信水平的最大潜在损失 |
| CVaR | 尾部损失的期望值 |
| 胜率 | 正收益天数占比 |
| 盈亏比 | 总盈利 / 总亏损 |

## 适用人群

- **个人投资者** — 持仓诊断、基金筛选、组合构建
- **基金研究员** — 批量分析、归因分析、报告生成
- **金融求职者** — 量化分析作品集、展示 Python + 金融交叉能力

## 注意事项

1. 数据来源于天天基金网公开数据，通过 akshare 接口获取
2. 本工具**不构成任何投资建议**
3. 过往业绩不代表未来表现
4. 建议结合实际市场环境和自身风险承受能力使用

## License

MIT
