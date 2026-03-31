"""
DeFiLlama 数据采集模块
提供 TVL、协议数据等 DeFi 相关信息
"""

import requests
from typing import Optional, Dict, Any, List
from datetime import datetime


BASE_URL = "https://api.llama.fi"
COINGECKO_MAP_URL = "https://coins.llama.fi"


def search_protocol(query: str) -> List[Dict[str, Any]]:
    """
    搜索 DeFi 协议
    
    Args:
        query: 搜索关键词
        
    Returns:
        协议列表
    """
    try:
        resp = requests.get(
            f"{BASE_URL}/search",
            params={"q": query},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("protocols", [])[:10]
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"DeFiLlama 搜索失败：{e}")


def get_protocol_data(protocol_slug: str) -> Dict[str, Any]:
    """
    获取协议详细数据
    
    Args:
        protocol_slug: 协议 slug（如 "uniswap", "aave"）
        
    Returns:
        协议数据字典
    """
    try:
        resp = requests.get(
            f"{BASE_URL}/protocol/{protocol_slug}",
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return {}
        raise RuntimeError(f"DeFiLlama 获取协议数据失败：{e}")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"网络请求失败：{e}")


def get_tvl_by_gecko_id(coin_id: str) -> Optional[Dict[str, Any]]:
    """
    根据 CoinGecko ID 获取 TVL 数据
    
    Args:
        coin_id: CoinGecko coin ID
        
    Returns:
        TVL 数据字典，包含 tvl、tvl_change_24h 等
    """
    try:
        # DeFiLlama 的 CoinGecko 映射接口
        resp = requests.get(
            f"{COINGECKO_MAP_URL}/prices/coingecko/{coin_id}",
            timeout=10,
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json()
        
        # 解析数据
        coins_data = data.get("coins", {})
        if coin_id in coins_data:
            price_data = coins_data[coin_id]
            return {
                "tvl": price_data.get("tvl"),
                "tvl_change_24h": price_data.get("tvlChange24h"),
                "mcap_to_tvl": price_data.get("mcapToTvl"),
                "fdv_to_tvl": price_data.get("fdvToTvl"),
            }
        return None
    except requests.exceptions.RequestException:
        return None


def get_all_protocols() -> List[Dict[str, Any]]:
    """
    获取所有协议列表（轻量版）
    
    Returns:
        协议列表
    """
    try:
        resp = requests.get(
            f"{BASE_URL}/protocols",
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"DeFiLlama 获取协议列表失败：{e}")


def get_defi_tvl_summary() -> Dict[str, Any]:
    """
    获取 DeFi 总 TVL 概览
    
    Returns:
        TVL 概览数据
    """
    try:
        resp = requests.get(
            f"{BASE_URL}/tvl",
            timeout=10,
        )
        resp.raise_for_status()
        return {"total_tvl": resp.json()}
    except requests.exceptions.RequestException:
        return {}


def enrich_token_data(coin_id: str, token_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    用 DeFiLlama 数据丰富 token 数据
    
    Args:
        coin_id: CoinGecko coin ID
        token_data: 现有的 token 数据
        
    Returns:
        丰富后的 token 数据
    """
    # 尝试获取 TVL 数据
    tvl_data = get_tvl_by_gecko_id(coin_id)
    
    if tvl_data:
        token_data["tvl_usd"] = tvl_data.get("tvl")
        token_data["tvl_change_24h"] = tvl_data.get("tvl_change_24h")
        token_data["mcap_to_tvl"] = tvl_data.get("mcap_to_tvl")
        token_data["fdv_to_tvl"] = tvl_data.get("fdv_to_tvl")
        
        # 判断是否为 DeFi 项目
        token_data["is_defi"] = tvl_data.get("tvl") is not None and tvl_data.get("tvl") > 0
    else:
        token_data["tvl_usd"] = None
        token_data["tvl_change_24h"] = None
        token_data["mcap_to_tvl"] = None
        token_data["fdv_to_tvl"] = None
        token_data["is_defi"] = False
    
    return token_data


# 链的 TVL 排名
def get_chain_tvl(chain: str) -> Optional[Dict[str, Any]]:
    """
    获取特定链的 TVL 数据
    
    Args:
        chain: 链名称（如 "Ethereum", "BSC"）
        
    Returns:
        链 TVL 数据
    """
    try:
        resp = requests.get(
            f"{BASE_URL}/v2/chains",
            timeout=10,
        )
        resp.raise_for_status()
        chains = resp.json()
        
        for chain_data in chains:
            if chain_data.get("name", "").lower() == chain.lower():
                return {
                    "chain": chain_data.get("name"),
                    "tvl": chain_data.get("tvl"),
                    "tvl_change_1d": chain_data.get("change_1d"),
                }
        return None
    except requests.exceptions.RequestException:
        return None
