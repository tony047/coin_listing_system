"""
CoinGecko 数据采集模块
唯一数据源，负责搜索 Token 和拉取完整评估数据
"""

import os
import re
import requests
import time
from typing import Optional

try:
    from ..utils.logger import get_logger, log_function_call
except ImportError:
    from utils.logger import get_logger, log_function_call

logger = get_logger()

# 主流交易所白名单，用于 tickers 裁剪
MAJOR_EXCHANGES = {
    "Binance", "OKX", "Bybit", "Coinbase Exchange", "Kraken",
    "Bitget", "Gate", "BYDFi", "KuCoin", "HTX",
    "MEXC", "Bitfinex", "Gemini", "Crypto.com Exchange"
}

BASE_URL = "https://api.coingecko.com/api/v3"


def _is_contract_address(query: str) -> bool:
    """检测是否为合约地址"""
    query = query.strip().lower()
    # 以太坊/BSC/Polygon 等 EVM 链地址：0x 开头，42位
    if re.match(r'^0x[a-f0-9]{40}$', query):
        return True
    # Solana 地址：32-44位 base58 字符
    if re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', query):
        return True
    return False


def _get_headers() -> dict:
    """构造请求头，有真实 API Key 时带上（排除占位符）"""
    api_key = os.getenv("COINGECKO_API_KEY", "").strip()
    if api_key and not api_key.startswith("CG-...") and len(api_key) > 10:
        return {"x-cg-demo-api-key": api_key}
    return {}


@log_function_call
def search_token(query: str) -> list[dict]:
    """
    搜索 Token，返回候选列表
    支持：名称、符号、合约地址（EVM/Solana）
    返回格式：[{"id": "sui", "name": "Sui", "symbol": "SUI"}, ...]
    """
    query = query.strip()
    
    # 如果是合约地址，使用合约地址搜索
    if _is_contract_address(query):
        return _search_by_contract_address(query)
    
    # 否则使用普通名称/符号搜索
    start_time = time.time()
    endpoint = f"{BASE_URL}/search"
    params = {"query": query}

    try:
        logger.api_call("CoinGecko", endpoint, params)

        resp = requests.get(
            endpoint,
            params=params,
            headers=_get_headers(),
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        coins = data.get("coins", [])

        # 只返回前 8 个候选，够用
        result = [
            {
                "id": c["id"],
                "name": c["name"],
                "symbol": c.get("symbol", "").upper(),
            }
            for c in coins[:8]
        ]

        duration = time.time() - start_time
        logger.api_success("CoinGecko.search_token", duration)
        logger.info(f"Found {len(result)} tokens for query: {query}")

        return result

    except requests.exceptions.HTTPError as e:
        duration = time.time() - start_time
        if e.response.status_code == 429:
            error_msg = "CoinGecko 请求频率过高，请稍后重试"
            logger.api_error("CoinGecko.search_token", RuntimeError(error_msg), duration)
            raise RuntimeError(error_msg)
        error_msg = f"CoinGecko 搜索失败：{e}"
        logger.api_error("CoinGecko.search_token", RuntimeError(error_msg), duration)
        raise RuntimeError(error_msg)
    except requests.exceptions.RequestException as e:
        duration = time.time() - start_time
        error_msg = f"网络请求失败：{e}"
        logger.api_error("CoinGecko.search_token", RuntimeError(error_msg), duration)
        raise RuntimeError(error_msg)
    except Exception as e:
        duration = time.time() - start_time
        error_msg = f"搜索过程中发生未知错误：{e}"
        logger.api_error("CoinGecko.search_token", RuntimeError(error_msg), duration)
        raise RuntimeError(error_msg)


def _search_by_contract_address(address: str) -> list[dict]:
    """
    通过合约地址搜索 Token
    自动检测链类型并尝试匹配
    """
    start_time = time.time()
    address = address.strip().lower()
    
    # 确定要尝试的平台列表
    platforms_to_try = []
    
    if address.startswith("0x"):
        # EVM 链地址，按优先级尝试
        platforms_to_try = [
            "ethereum",
            "binance-smart-chain",
            "polygon-pos",
            "arbitrum-one",
            "avalanche",
            "base",
            "optimistic-ethereum",
        ]
    else:
        # Solana 地址
        platforms_to_try = ["solana"]
    
    for platform in platforms_to_try:
        try:
            endpoint = f"{BASE_URL}/coins/{platform}/contract/{address}"
            logger.api_call("CoinGecko", endpoint, {})
            
            resp = requests.get(
                endpoint,
                headers=_get_headers(),
                timeout=10,
            )
            
            if resp.status_code == 200:
                data = resp.json()
                result = [{
                    "id": data.get("id"),
                    "name": data.get("name"),
                    "symbol": data.get("symbol", "").upper(),
                    "platform": platform,
                    "contract_address": address,
                }]
                duration = time.time() - start_time
                logger.api_success("CoinGecko.contract_search", duration)
                logger.info(f"Found token by contract: {data.get('name')} ({data.get('symbol')}) on {platform}")
                return result
        except requests.exceptions.HTTPError:
            continue
        except Exception as e:
            logger.info(f"Contract not found on {platform}: {e}")
            continue
    
    # 所有平台都没找到
    duration = time.time() - start_time
    logger.info(f"Contract address not found on any platform: {address}")
    # 返回特殊标识，表示可能是钱包地址
    return [{"_is_wallet_address": True, "query": address}]


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


@log_function_call
def get_token_data(coin_id: str) -> dict:
    """
    拉取 Token 完整数据，返回结构化字典
    包含：市场数据、社区数据、开发者数据、交易所列表
    """
    start_time = time.time()
    endpoint = f"{BASE_URL}/coins/{coin_id}"
    params = {
        "tickers": "true",
        "market_data": "true",
        "community_data": "true",
        "developer_data": "true",
        "sparkline": "false",
    }

    try:
        logger.api_call("CoinGecko", endpoint, params)
        logger.info(f"Fetching data for token: {coin_id}")

        resp = requests.get(
            endpoint,
            params=params,
            headers=_get_headers(),
            timeout=15,
        )
        resp.raise_for_status()
        raw = resp.json()

        duration = time.time() - start_time
        logger.api_success("CoinGecko.get_token_data", duration)

    except requests.exceptions.HTTPError as e:
        duration = time.time() - start_time
        if e.response.status_code == 404:
            error_msg = f"未找到 Token：{coin_id}"
            logger.api_error("CoinGecko.get_token_data", RuntimeError(error_msg), duration)
            raise RuntimeError(error_msg)
        if e.response.status_code == 429:
            error_msg = "CoinGecko 请求频率过高，请稍后重试"
            logger.api_error("CoinGecko.get_token_data", RuntimeError(error_msg), duration)
            raise RuntimeError(error_msg)
        error_msg = f"CoinGecko 数据获取失败：{e}"
        logger.api_error("CoinGecko.get_token_data", RuntimeError(error_msg), duration)
        raise RuntimeError(error_msg)
    except requests.exceptions.RequestException as e:
        duration = time.time() - start_time
        error_msg = f"网络请求失败：{e}"
        logger.api_error("CoinGecko.get_token_data", RuntimeError(error_msg), duration)
        raise RuntimeError(error_msg)
    except Exception as e:
        duration = time.time() - start_time
        error_msg = f"获取 Token 数据时发生未知错误：{e}"
        logger.api_error("CoinGecko.get_token_data", RuntimeError(error_msg), duration)
        raise RuntimeError(error_msg)

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

        # 社区数据
        # CoinGecko 免费版 Reddit/Twitter 数据已不可用（均返回0或null）
        # 改用 watchlist_portfolio_users 和 sentiment_votes 作为社区关注度指标
        "telegram_members": community.get("telegram_channel_user_count"),
        "reddit_subscribers": community.get("reddit_subscribers"),
        "watchlist_users": raw.get("watchlist_portfolio_users"),
        "sentiment_up_pct": raw.get("sentiment_votes_up_percentage"),

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

        # 供应量数据（用于 Tokenomics 分析）
        "total_supply": market.get("total_supply"),
        "circulating_supply": market.get("circulating_supply"),
        "max_supply": market.get("max_supply"),

        # 合约地址（用于链上数据分析）
        # 格式：{"ethereum": "0x...", "solana": "...", "binance-smart-chain": "0x..."}
        "platforms": raw.get("platforms", {}),
    }


def _safe_get(d: dict, *keys) -> Optional[float]:
    """安全的嵌套字典取值"""
    for key in keys:
        if not isinstance(d, dict):
            return None
        d = d.get(key)
    return d
