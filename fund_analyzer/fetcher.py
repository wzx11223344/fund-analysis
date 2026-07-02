"""
基金数据获取模块
==============
基于 akshare 开源库，无需 API Key，
免费获取中国公募基金公开数据。

支持的 akshare 接口:
    - fund_open_fund_rank_em     基金排名列表
    - fund_open_fund_info_em     基金基本信息
    - fund_open_fund_hist_em     历史净值
    - fund_open_fund_hold_em     持仓明细
    - fund_manager_interface     基金经理
    - fund_rating_all            基金评级
    - fund_open_fund_daily_em    每日开放式基金
"""

import time
import json
import os
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Union

import pandas as pd
import akshare as ak

# ---------------------------------------------------------------------------
# 缓存配置
# ---------------------------------------------------------------------------
CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "cache")
CACHE_TTL = {
    "search": 300,           # 5 分钟
    "info": 86400,           # 1 天
    "nav": 3600,             # 1 小时
    "returns": 3600,         # 1 小时
    "holdings": 86400,       # 1 天
    "manager": 86400,        # 1 天
    "rating": 86400,         # 1 天
    "fund_types": 86400,     # 1 天
}
os.makedirs(CACHE_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _cache_key(name: str, *args, **kwargs) -> str:
    """生成缓存文件名."""
    raw = name + "|" + "|".join(str(a) for a in args) + "|" + json.dumps(kwargs, sort_keys=True)
    h = hashlib.md5(raw.encode()).hexdigest()
    return os.path.join(CACHE_DIR, f"{name}_{h}.json")


def _load_cache(filepath: str, max_age: int) -> Optional[Union[dict, list]]:
    """读取缓存，过期返回 None."""
    if not os.path.isfile(filepath):
        return None
    age = time.time() - os.path.getmtime(filepath)
    if age > max_age:
        return None
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _save_cache(filepath: str, data):
    """写入缓存."""
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, default=str)
    except OSError:
        pass  # 缓存写入失败不影响主流程


def _retry(func, retries=3, delay=1):
    """带指数退避的重试装饰."""
    for attempt in range(retries):
        try:
            return func()
        except Exception as e:
            if attempt == retries - 1:
                raise
            time.sleep(delay * (2 ** attempt))


def _df_to_dict_list(df: pd.DataFrame) -> list:
    """DataFrame -> list[dict]."""
    if df is None or df.empty:
        return []
    return df.to_dict(orient="records")


def _safe_date_parse(val) -> Optional[str]:
    """安全格式化日期."""
    if pd.isna(val) or val is None:
        return None
    try:
        dt = pd.Timestamp(val)
        return dt.strftime("%Y-%m-%d") if not pd.isna(dt) else None
    except (ValueError, TypeError):
        return str(val)


# ---------------------------------------------------------------------------
# 公开 API
# ---------------------------------------------------------------------------

def search_fund(keyword: str, page: int = 1, page_size: int = 50) -> list:
    """
    按名称或代码搜索基金。

    参数:
        keyword: 基金名称或代码 (如 "沪深300", "110020")
        page: 页码 (从 1 开始)
        page_size: 每页数量

    返回:
        list[dict]: [{"code": "110020", "name": "易方达沪深300ETF联接A", "type": "...", ...}, ...]
    """
    ck = _cache_key("search", keyword, page, page_size=page_size)
    cached = _load_cache(ck, CACHE_TTL["search"])
    if cached is not None:
        return cached

    def _fetch():
        df = ak.fund_open_fund_rank_em()
        if df is None or df.empty:
            return []
        # 统一列名（akshare 版本间可能变化）
        col_map = {
            "基金代码": "code",
            "基金简称": "name",
            "基金类型": "type",
            "日期": "date",
            "单位净值": "nav",
            "累计净值": "acc_nav",
            "日增长率": "daily_return",
            "近1周": "ret_1w",
            "近1月": "ret_1m",
            "近3月": "ret_3m",
            "近6月": "ret_6m",
            "近1年": "ret_1y",
            "近2年": "ret_2y",
            "近3年": "ret_3y",
            "今年来": "ret_ytd",
            "成立来": "ret_since_inception",
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
        # 过滤匹配
        keyword_lower = keyword.lower()
        mask = df["name"].str.lower().str.contains(keyword_lower, na=False) | df["code"].astype(str).str.contains(keyword_lower, na=False)
        result = df[mask].to_dict(orient="records")
        return result

    data = _retry(_fetch)
    _save_cache(ck, data)
    return data


def get_fund_info(fund_code: str) -> dict:
    """
    获取基金基本信息。

    参数:
        fund_code: 基金代码 (如 "110020")

    返回:
        dict: 基金名称、类型、管理人、规模、成立日期等
    """
    ck = _cache_key("info", fund_code)
    cached = _load_cache(ck, CACHE_TTL["info"])
    if cached is not None:
        return cached

    def _fetch():
        try:
            df = ak.fund_open_fund_info_em(symbol=fund_code, indicator="基金规模")
        except Exception:
            df = pd.DataFrame()
        if df is None or df.empty:
            return {}

        info = {}
        for _, row in df.iterrows():
            key = str(row.iloc[0]).strip() if len(row) > 0 else ""
            val = str(row.iloc[1]).strip() if len(row) > 1 else ""
            info[key] = val

        # 结构化输出
        result = {
            "code": fund_code,
            "name": info.get("基金简称", ""),
            "type": info.get("基金类型", ""),
            "manager_company": info.get("管理人", ""),
            "custodian": info.get("托管人", ""),
            "inception_date": info.get("成立日期", ""),
            "listing_date": info.get("上市日期", ""),
            "issuer": info.get("发行方", ""),
            "management_fee": info.get("管理费", ""),
            "custody_fee": info.get("托管费", ""),
            "service_fee": info.get("销售服务费", ""),
            "latest_size": info.get("最新规模", ""),
            "size_date": info.get("规模日期", ""),
        }
        return result

    data = _retry(_fetch)
    _save_cache(ck, data)
    return data


def get_fund_nav(fund_code: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
    """
    获取基金历史净值数据。

    参数:
        fund_code: 基金代码
        start_date: 起始日期 "YYYY-MM-DD"，默认一年前
        end_date: 结束日期 "YYYY-MM-DD"，默认今天

    返回:
        pd.DataFrame: 包含日期、单位净值、累计净值、日涨跌幅
    """
    if end_date is None:
        end_date = datetime.today().strftime("%Y-%m-%d")
    if start_date is None:
        start_date = (datetime.today() - timedelta(days=365)).strftime("%Y-%m-%d")

    ck = _cache_key("nav", fund_code, start_date, end_date)
    cached = _load_cache(ck, CACHE_TTL["nav"])
    if cached is not None:
        return pd.DataFrame(cached)

    def _fetch():
        df = ak.fund_open_fund_hist_em(
            symbol=fund_code,
            indicator="累计净值",
            start_date=start_date,
            end_date=end_date,
        )
        if df is None or df.empty:
            return pd.DataFrame()

        # 标准化列名
        col_map = {
            "净值日期": "date",
            "单位净值": "nav",
            "累计净值": "acc_nav",
            "日增长率": "daily_return",
            "日增长额": "daily_change",
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
        for col in ["nav", "acc_nav", "daily_return"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.sort_values("date").reset_index(drop=True)
        return df

    df = _retry(_fetch)
    if not df.empty:
        _save_cache(ck, _df_to_dict_list(df))
    return df


def get_fund_returns(fund_code: str) -> dict:
    """
    获取基金各区间收益率。

    参数:
        fund_code: 基金代码

    返回:
        dict: {"近1月": 0.05, "近3月": 0.12, ...}
    """
    ck = _cache_key("returns", fund_code)
    cached = _load_cache(ck, CACHE_TTL["returns"])
    if cached is not None:
        return cached

    def _fetch():
        df = ak.fund_open_fund_rank_em()
        if df is None or df.empty:
            return {}

        match = df[df["基金代码"].astype(str) == str(fund_code)]
        if match.empty:
            return {}

        row = match.iloc[0]
        period_map = {
            "近1周": "1w",
            "近1月": "1m",
            "近3月": "3m",
            "近6月": "6m",
            "近1年": "1y",
            "近2年": "2y",
            "近3年": "3y",
            "今年来": "ytd",
            "成立来": "since_inception",
        }
        result = {}
        for cn_key, en_key in period_map.items():
            val = row.get(cn_key)
            if val is not None:
                try:
                    result[en_key] = float(val) / 100.0  # 百分比 → 小数
                except (ValueError, TypeError):
                    pass
        return result

    data = _retry(_fetch)
    _save_cache(ck, data)
    return data


def get_fund_holdings(fund_code: str, date: str = None) -> list:
    """
    获取基金前十大持仓。

    参数:
        fund_code: 基金代码
        date: 报告期日期 "YYYY-MM-DD"，默认最新

    返回:
        list[dict]: [{"stock_name": "贵州茅台", "stock_code": "600519", "ratio": 0.0986, ...}, ...]
    """
    ck = _cache_key("holdings", fund_code, date or "latest")
    cached = _load_cache(ck, CACHE_TTL["holdings"])
    if cached is not None:
        return cached

    def _fetch():
        df = ak.fund_open_fund_hold_em(symbol=fund_code, date=date)
        if df is None or df.empty:
            return []

        col_map = {
            "股票代码": "stock_code",
            "股票名称": "stock_name",
            "占净值比例": "ratio",
            "持股数": "shares",
            "持仓市值": "market_value",
            "报告期": "report_date",
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

        for col in ["ratio", "shares", "market_value"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        if "ratio" in df.columns:
            df["ratio"] = df["ratio"] / 100.0  # 百分比 → 小数

        records = _df_to_dict_list(df)

        # 尝试获取行业信息（如有）
        try:
            industry_df = ak.fund_open_fund_hold_em(symbol=fund_code, date=date, indicator="行业")
            if industry_df is not None and not industry_df.empty:
                industry_col_map = {
                    "行业名称": "industry_name",
                    "占净值比例": "industry_ratio",
                }
                industry_df = industry_df.rename(columns={k: v for k, v in industry_col_map.items() if k in industry_df.columns})
                if "industry_ratio" in industry_df.columns:
                    industry_df["industry_ratio"] = pd.to_numeric(industry_df["industry_ratio"], errors="coerce") / 100.0
                records.append({"__industry_breakdown": _df_to_dict_list(industry_df)})
        except Exception:
            pass

        return records

    data = _retry(_fetch)
    _save_cache(ck, data)
    return data


def get_fund_manager(fund_code: str) -> dict:
    """
    获取基金经理信息。

    参数:
        fund_code: 基金代码

    返回:
        dict: 经理姓名、任职日期、从业年限、管理基金数等
    """
    ck = _cache_key("manager", fund_code)
    cached = _load_cache(ck, CACHE_TTL["manager"])
    if cached is not None:
        return cached

    def _fetch():
        df = ak.fund_manager_interface()
        if df is None or df.empty:
            return {}

        match = df[df["基金代码"].astype(str) == str(fund_code)]
        if match.empty:
            return {}

        row = match.iloc[0]
        result = {
            "manager_name": row.get("基金经理", ""),
            "tenure_start": str(row.get("任职日期", "")),
            "management_fee": row.get("管理费", ""),
            "fund_type": row.get("基金类型", ""),
            "fund_scale": row.get("基金规模", ""),
        }
        return result

    data = _retry(_fetch)
    _save_cache(ck, data)
    return data


def get_fund_rating(fund_code: str) -> dict:
    """
    获取基金评级信息。

    参数:
        fund_code: 基金代码

    返回:
        dict: {"综合评级": 5, "三年评级": 5, "五年评级": 4, ...}
    """
    ck = _cache_key("rating", fund_code)
    cached = _load_cache(ck, CACHE_TTL["rating"])
    if cached is not None:
        return cached

    def _fetch():
        try:
            df = ak.fund_rating_all()
        except Exception:
            return {}

        if df is None or df.empty:
            return {}

        match = df[df["基金代码"].astype(str) == str(fund_code)]
        if match.empty:
            return {}

        row = match.iloc[0]
        rating_keys = [
            "综合星级", "三年评级", "五年评级",
            "过去一年星级评价", "过去两年星级评价",
            "过去三年星级评价", "过去五年星级评价",
        ]
        result = {}
        for key in rating_keys:
            if key in row:
                try:
                    result[key] = int(float(row[key]))
                except (ValueError, TypeError):
                    result[key] = row[key]
        return result

    data = _retry(_fetch)
    _save_cache(ck, data)
    return data


def get_all_fund_types() -> list:
    """
    获取所有基金类型列表。

    返回:
        list[dict]: [{"type": "股票型", "count": 2000}, ...]
    """
    ck = _cache_key("fund_types")
    cached = _load_cache(ck, CACHE_TTL["fund_types"])
    if cached is not None:
        return cached

    def _fetch():
        df = ak.fund_open_fund_rank_em()
        if df is None or df.empty:
            return []

        type_col = None
        for candidate in ["基金类型", "基金分类", "类型"]:
            if candidate in df.columns:
                type_col = candidate
                break
        if type_col is None:
            return []

        counts = df[type_col].value_counts()
        return [{"type": k, "count": int(v)} for k, v in counts.items()]

    data = _retry(_fetch)
    _save_cache(ck, data)
    return data


def clear_cache():
    """清空所有缓存."""
    for fname in os.listdir(CACHE_DIR):
        fpath = os.path.join(CACHE_DIR, fname)
        try:
            if os.path.isfile(fpath):
                os.remove(fpath)
        except OSError:
            pass
    print(f"[Fetcher] 缓存已清空: {CACHE_DIR}")
