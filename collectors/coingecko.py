"""
CoinGecko 数据采集模块
唯一数据源，负责搜索 Token 和拉取完整评估数据
"""

import os
import requests
from typing import Optional

# 主流交易所白名单，用于 tickers 裁剪
MAJOR_EXCHANGES = {
    "Binance", "OKX", "Bybit", "Coinbase Exchange", "Kraken",
    "Bitget", "Gate.io", "BYDFi", "KuCoin", "Huobi",
    "MEXC", "Bitfinex", "Gemini", "Crypto.com Exchange"
}

BASE_URL = "https://api.coingecko.com/api/v3"


def _get_headers() -> dict:
    """构造请求头，有真实 API Key 时带上（排除占位符）"""
    api_key = os.getenv("COINGECKO_API_KEY", "").strip()
    if api_key and not api_key.startswith("CG-...") and len(api_key) > 10:
        return {"x-cg-demo-api-key": api_key}
    return {}


def search_token(query: str) -> list[dict]:
    """
    搜索 Token，返回候选列表
    返回格式：[{"id": "sui", "name": "Sui", "symbol": "SUI"}, ...]
    """
    try:
        resp = requests.get(
            f"{BASE_URL}/search",
            params={"query": query},
            headers=_get_headers(),
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        coins = data.get("coins", [])
        # 只返回前 8 个候选，够用
        return [
            {
                "id": c["id"],
                "name": c["name"],
                "symbol": c.get("symbol", "").upper(),
            }
            for c in coins[:8]
        ]
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            raise RuntimeError("CoinGecko 请求频率过高，请稍后重试")
        raise RuntimeError(f"CoinGecko 搜索失败：{e}")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"网络请求失败：{e}")


def extract_listed_exchanges(tickers: list) -> tuple[list[str], int]:
    """
    从 tickers 数组中提取主流交易所列表
    返回：(主流所名称列表, 其他交易所数量)
    """
    if not tickers:
        return [], 0
    all_names = {t["market"]["name"] for t in tickers if t.get("market")}
    major = sorted(all_names & MAJOR_EXCHANGES)
    others_count = len(all_names) - len(major)
    return major, others_count


def get_token_data(coin_id: str) -> dict:
    """
    拉取 Token 完整数据，返回结构化字典
    包含：市场数据、社区数据、开发者数据、交易所列表
    """
    try:
        resp = requests.get(
            f"{BASE_URL}/coins/{coin_id}",
            params={
                "tickers": "true",
                "market_data": "true",
                "community_data": "true",
                "developer_data": "true",
                "sparkline": "false",
            },
            headers=_get_headers(),
            timeout=15,
        )
        resp.raise_for_status()
        raw = resp.json()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            raise RuntimeError(f"未找到 Token：{coin_id}")
        if e.response.status_code == 429:
            raise RuntimeError("CoinGecko 请求频率过高，请稍后重试")
        raise RuntimeError(f"CoinGecko 数据获取失败：{e}")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"网络请求失败：{e}")

    market = raw.get("market_data", {})
    community = raw.get("community_data", {})
    developer = raw.get("developer_data", {})
    tickers = raw.get("tickers", [])

    # 提取交易所列表
    listed_on_major, other_exchanges_count = extract_listed_exchanges(tickers)
    listed_on_bydfi = "BYDFi" in listed_on_major

    return {
        # 基础信息
        "id": raw.get("id"),
        "name": raw.get("name"),
        "symbol": raw.get("symbol", "").upper(),
        "description": raw.get("description", {}).get("en", "")[:500],

        # 市场数据
        "market_cap_usd": _safe_get(market, "market_cap", "usd"),
        "volume_24h_usd": _safe_get(market, "total_volume", "usd"),
        "price_usd": _safe_get(market, "current_price", "usd"),
        "price_change_24h": market.get("price_change_percentage_24h"),
        "price_change_30d": market.get("price_change_percentage_30d"),
        "market_cap_rank": raw.get("market_cap_rank"),

        # 社区数据（CoinGecko 免费版不提供 Twitter 粉丝数）
        "telegram_members": community.get("telegram_channel_user_count"),
        "reddit_subscribers": community.get("reddit_subscribers"),

        # 开发者数据（来自 CoinGecko developer_data，无需调 GitHub API）
        "github_stars": developer.get("stars"),
        "github_forks": developer.get("forks"),
        "commit_count_4_weeks": developer.get("commit_count_4_weeks"),
        "commit_activity_series": developer.get("last_4_weeks_commit_activity_series", []),

        # 交易所数据（实时，不依赖 Claude 记忆）
        "listed_on_major": listed_on_major,
        "listed_on_other_count": other_exchanges_count,
        "listed_on_bydfi": listed_on_bydfi,
        "total_tickers": len(tickers),
    }


def _safe_get(d: dict, *keys) -> Optional[float]:
    """安全的嵌套字典取值"""
    for key in keys:
        if not isinstance(d, dict):
            return None
        d = d.get(key)
    return d
