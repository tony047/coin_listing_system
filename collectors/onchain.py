"""
链上数据采集器
通过 Etherscan/Solscan 等免费 API 获取 Token 持有者分布数据
"""

import os
import requests
from typing import Dict, Any, Optional

try:
    from ..utils.logger import get_logger
except ImportError:
    from utils.logger import get_logger

logger = get_logger()

# API 配置
ETHERSCAN_BASE_URL = "https://api.etherscan.io/api"
SOLSCAN_BASE_URL = "https://api.solscan.io"

# 链名称映射（CoinGecko platforms 字段 -> 我们的标准化链名）
CHAIN_PRIORITY = ["ethereum", "binance-smart-chain", "solana"]
CHAIN_MAPPING = {
    "ethereum": "ethereum",
    "binance-smart-chain": "bsc",
    "solana": "solana",
}

# API 超时配置
API_TIMEOUT = 5


def get_onchain_data(coingecko_data: dict) -> dict:
    """
    获取链上数据
    
    从 CoinGecko 数据中提取合约地址，然后查询链上持有者数据。
    
    Args:
        coingecko_data: get_token_data() 返回的完整数据
    
    Returns:
        {
            'chain': str,  # 'ethereum', 'solana', 'bsc', 'unknown'
            'contract_address': str or None,
            'top_holders_pct': float or None,  # Top 10 持有者占比 (0-1)
            'total_holders': int or None,  # 持有者总数
            'concentration_risk': str,  # 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'UNKNOWN'
            'data_available': bool,
            'data_source': str  # 'etherscan', 'solscan', 'estimation', 'none'
        }
    """
    # 默认返回值
    default_result = {
        "chain": "unknown",
        "contract_address": None,
        "top_holders_pct": None,
        "total_holders": None,
        "concentration_risk": "UNKNOWN",
        "data_available": False,
        "data_source": "none",
    }
    
    # 1. 提取合约地址
    platforms = coingecko_data.get("platforms", {})
    if not platforms:
        logger.info("无 platforms 数据，使用降级估算方案")
        return _estimate_holders_from_supply(coingecko_data)
    
    # 按优先级查找合约地址
    chain = None
    contract_address = None
    for platform in CHAIN_PRIORITY:
        if platform in platforms and platforms[platform]:
            chain = CHAIN_MAPPING.get(platform, platform)
            contract_address = platforms[platform]
            break
    
    # 如果优先链没找到，使用第一个可用的
    if not contract_address:
        for platform, address in platforms.items():
            if address:
                chain = CHAIN_MAPPING.get(platform, platform)
                contract_address = address
                break
    
    if not contract_address:
        logger.info("所有 platforms 地址为空，使用降级估算方案")
        return _estimate_holders_from_supply(coingecko_data)
    
    logger.info(f"找到合约地址: {chain} - {contract_address[:20]}...")
    
    # 2. 根据链类型调用对应 API
    if chain == "ethereum":
        result = _get_etherscan_holders(contract_address)
    elif chain == "bsc":
        result = _get_bscscan_holders(contract_address)
    elif chain == "solana":
        result = _get_solscan_holders(contract_address)
    else:
        result = None
    
    # 3. 如果链上 API 失败，使用降级方案
    if result is None:
        logger.info(f"链上 API 数据获取失败，使用降级估算方案")
        result = _estimate_holders_from_supply(coingecko_data)
    
    # 填充合约信息
    result["chain"] = chain
    result["contract_address"] = contract_address
    
    return result


def _get_etherscan_holders(contract_address: str) -> Optional[dict]:
    """
    通过 Etherscan API 获取 Token 持有者数据
    
    注意：Etherscan 免费版的 tokenholderlist 需要 Pro 版
    这里尝试调用，失败则返回 None 由上层降级处理
    """
    api_key = os.getenv("ETHERSCAN_API_KEY", "").strip()
    
    if not api_key or api_key.startswith("your_"):
        logger.info("Etherscan API Key 未配置，跳过链上数据获取")
        return None
    
    try:
        # 尝试获取 Top 10 持有者
        params = {
            "module": "token",
            "action": "tokenholderlist",
            "contractaddress": contract_address,
            "page": 1,
            "offset": 10,
            "apikey": api_key,
        }
        
        logger.info(f"调用 Etherscan API: tokenholderlist")
        resp = requests.get(ETHERSCAN_BASE_URL, params=params, timeout=API_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        
        # 检查 API 返回状态
        if data.get("status") != "1":
            error_msg = data.get("message", "Unknown error")
            logger.warning(f"Etherscan API 返回错误: {error_msg}")
            
            # 如果是 Pro 限制，尝试其他方法
            if "pro" in error_msg.lower() or "upgrade" in error_msg.lower():
                logger.info("Etherscan tokenholderlist 需要 Pro 版，尝试其他方法")
                return _get_etherscan_token_info(contract_address, api_key)
            
            return None
        
        # 解析持有者数据
        holders = data.get("result", [])
        if not holders:
            return None
        
        # 计算 Top 10 持有者占比
        total_top_10 = sum(int(h.get("TokenHolderQuantity", 0)) for h in holders)
        
        # 获取总供应量来计算占比
        supply_params = {
            "module": "stats",
            "action": "tokensupply",
            "contractaddress": contract_address,
            "apikey": api_key,
        }
        supply_resp = requests.get(ETHERSCAN_BASE_URL, params=supply_params, timeout=API_TIMEOUT)
        supply_data = supply_resp.json()
        
        total_supply = int(supply_data.get("result", 0)) if supply_data.get("status") == "1" else 0
        
        if total_supply > 0:
            top_holders_pct = total_top_10 / total_supply
        else:
            top_holders_pct = None
        
        return {
            "chain": "ethereum",
            "contract_address": contract_address,
            "top_holders_pct": top_holders_pct,
            "total_holders": len(holders),  # 这只是 Top 10，不是真实总数
            "concentration_risk": _calculate_concentration_risk(top_holders_pct),
            "data_available": True,
            "data_source": "etherscan",
        }
        
    except requests.exceptions.Timeout:
        logger.warning(f"Etherscan API 超时")
        return None
    except requests.exceptions.RequestException as e:
        logger.warning(f"Etherscan API 请求失败: {e}")
        return None
    except Exception as e:
        logger.warning(f"Etherscan 数据解析异常: {e}")
        return None


def _get_etherscan_token_info(contract_address: str, api_key: str) -> Optional[dict]:
    """
    通过 Etherscan Token Info API 获取基础数据
    这是 tokenholderlist 不可用时的备选方案
    """
    try:
        params = {
            "module": "token",
            "action": "tokeninfo",
            "contractaddress": contract_address,
            "apikey": api_key,
        }
        
        resp = requests.get(ETHERSCAN_BASE_URL, params=params, timeout=API_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        
        if data.get("status") != "1":
            return None
        
        result = data.get("result", [])
        if not result:
            return None
        
        token_info = result[0] if isinstance(result, list) else result
        total_holders = int(token_info.get("holdersCount", 0))
        
        return {
            "chain": "ethereum",
            "contract_address": contract_address,
            "top_holders_pct": None,  # tokeninfo 不提供具体占比
            "total_holders": total_holders if total_holders > 0 else None,
            "concentration_risk": _estimate_risk_from_holder_count(total_holders),
            "data_available": total_holders > 0,
            "data_source": "etherscan",
        }
        
    except Exception as e:
        logger.warning(f"Etherscan tokeninfo 失败: {e}")
        return None


def _get_bscscan_holders(contract_address: str) -> Optional[dict]:
    """
    通过 BscScan API 获取 BSC 链上持有者数据
    BscScan API 与 Etherscan 兼容
    """
    api_key = os.getenv("ETHERSCAN_API_KEY", "").strip()  # 可以复用 Etherscan key
    
    if not api_key or api_key.startswith("your_"):
        return None
    
    try:
        bscscan_url = "https://api.bscscan.com/api"
        params = {
            "module": "token",
            "action": "tokenholderlist",
            "contractaddress": contract_address,
            "page": 1,
            "offset": 10,
            "apikey": api_key,
        }
        
        logger.info(f"调用 BscScan API")
        resp = requests.get(bscscan_url, params=params, timeout=API_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        
        if data.get("status") != "1":
            return None
        
        holders = data.get("result", [])
        if not holders:
            return None
        
        # 简化处理，返回基础信息
        return {
            "chain": "bsc",
            "contract_address": contract_address,
            "top_holders_pct": None,
            "total_holders": len(holders),
            "concentration_risk": "UNKNOWN",
            "data_available": True,
            "data_source": "bscscan",
        }
        
    except Exception as e:
        logger.warning(f"BscScan API 失败: {e}")
        return None


def _get_solscan_holders(contract_address: str) -> Optional[dict]:
    """
    通过 Solscan API 获取 Solana 链上持有者数据
    
    Solscan 公开 API 限制较多，这里做基础尝试
    """
    try:
        # Solscan 公开 API
        url = f"{SOLSCAN_BASE_URL}/token/holders"
        params = {
            "tokenAddress": contract_address,
            "offset": 0,
            "limit": 10,
        }
        
        logger.info(f"调用 Solscan API")
        resp = requests.get(url, params=params, timeout=API_TIMEOUT)
        
        if resp.status_code == 403 or resp.status_code == 401:
            logger.info("Solscan API 需要认证，跳过")
            return None
            
        resp.raise_for_status()
        data = resp.json()
        
        if "data" not in data:
            return None
        
        holders = data.get("data", [])
        total = data.get("total", 0)
        
        return {
            "chain": "solana",
            "contract_address": contract_address,
            "top_holders_pct": None,
            "total_holders": total if total > 0 else len(holders),
            "concentration_risk": _estimate_risk_from_holder_count(total),
            "data_available": True,
            "data_source": "solscan",
        }
        
    except Exception as e:
        logger.warning(f"Solscan API 失败: {e}")
        return None


def _estimate_holders_from_supply(coingecko_data: dict) -> dict:
    """
    基于 CoinGecko 数据估算持有者浓度
    
    使用以下启发式规则：
    - 如果 market_cap_rank <= 50: 大概率持有者分散 → LOW risk
    - 如果 market_cap_rank <= 200 且 volume_24h 高: MEDIUM risk  
    - 如果 market_cap_rank > 500 且 volume_24h 低: 可能集中 → HIGH risk
    - 如果有 DeFi TVL 数据且 TVL/marketcap 比例合理: 降低风险等级
    
    这是一个粗略估算，当链上 API 不可用时使用
    """
    rank = coingecko_data.get("market_cap_rank")
    volume = coingecko_data.get("volume_24h_usd") or 0
    market_cap = coingecko_data.get("market_cap_usd") or 0
    
    # TVL 数据（如果有的话）
    tvl = coingecko_data.get("tvl_usd") or 0
    
    # 默认风险等级
    risk = "UNKNOWN"
    estimated_holders_pct = None
    
    if rank is not None:
        if rank <= 50:
            # Top 50 代币通常持有者分散
            risk = "LOW"
            estimated_holders_pct = 0.15  # 估算 Top 10 持有约 15%
        elif rank <= 100:
            # Top 100 通常也比较分散
            if volume >= 50_000_000:  # 高流动性
                risk = "LOW"
                estimated_holders_pct = 0.18
            else:
                risk = "MEDIUM"
                estimated_holders_pct = 0.25
        elif rank <= 200:
            if volume >= 10_000_000:
                risk = "MEDIUM"
                estimated_holders_pct = 0.30
            else:
                risk = "MEDIUM"
                estimated_holders_pct = 0.35
        elif rank <= 500:
            if volume >= 5_000_000:
                risk = "MEDIUM"
                estimated_holders_pct = 0.35
            else:
                risk = "HIGH"
                estimated_holders_pct = 0.45
        else:
            # 排名 500 以后
            if volume >= 1_000_000:
                risk = "MEDIUM"
                estimated_holders_pct = 0.40
            else:
                risk = "HIGH"
                estimated_holders_pct = 0.50
    
    # TVL 调整：如果有 DeFi TVL 且比例合理，降低风险
    if tvl > 0 and market_cap > 0:
        tvl_ratio = tvl / market_cap
        if tvl_ratio > 0.5:  # TVL 超过市值一半，说明有真实使用场景
            if risk == "HIGH":
                risk = "MEDIUM"
            elif risk == "MEDIUM" and rank and rank <= 200:
                risk = "LOW"
    
    logger.info(f"使用估算方案: rank={rank}, volume={volume}, risk={risk}")
    
    return {
        "chain": "unknown",
        "contract_address": None,
        "top_holders_pct": estimated_holders_pct,
        "total_holders": None,
        "concentration_risk": risk,
        "data_available": True,
        "data_source": "estimation",
        "estimation_basis": {
            "market_cap_rank": rank,
            "volume_24h_usd": volume,
            "tvl_usd": tvl,
        }
    }


def _calculate_concentration_risk(top_holders_pct: Optional[float]) -> str:
    """
    根据 Top 10 持有者占比计算浓度风险等级
    
    - top_holders_pct > 0.6（Top 10 持有 > 60%）→ CRITICAL
    - top_holders_pct > 0.4（> 40%）→ HIGH
    - top_holders_pct > 0.2（> 20%）→ MEDIUM
    - top_holders_pct <= 0.2 → LOW
    - 数据不可用 → UNKNOWN
    """
    if top_holders_pct is None:
        return "UNKNOWN"
    
    if top_holders_pct > 0.6:
        return "CRITICAL"
    elif top_holders_pct > 0.4:
        return "HIGH"
    elif top_holders_pct > 0.2:
        return "MEDIUM"
    else:
        return "LOW"


def _estimate_risk_from_holder_count(total_holders: int) -> str:
    """
    根据持有者总数估算风险等级
    
    - 持有者 < 1000: 高风险
    - 持有者 1000-5000: 中等风险
    - 持有者 > 5000: 低风险
    """
    if total_holders is None or total_holders <= 0:
        return "UNKNOWN"
    
    if total_holders < 1000:
        return "HIGH"
    elif total_holders < 5000:
        return "MEDIUM"
    else:
        return "LOW"
