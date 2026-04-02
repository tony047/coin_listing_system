"""
Tokenomics 数据分析模块
从 CoinGecko 数据中提取代币经济学指标
"""

from typing import Optional

try:
    from ..utils.logger import get_logger
except ImportError:
    from utils.logger import get_logger

logger = get_logger()


def analyze_tokenomics(coingecko_data: dict) -> dict:
    """
    从 CoinGecko 已有数据中提取 Tokenomics 指标
    
    Args:
        coingecko_data: get_token_data() 返回的完整数据
    
    Returns:
        {
            'total_supply': float or None,
            'circulating_supply': float or None,
            'max_supply': float or None,
            'circulation_ratio': float or None,  # circulating / total
            'has_max_supply': bool,  # 是否有最大供应量限制
            'is_deflationary': bool,  # max_supply 是否等于 total_supply（可能通缩）
            'supply_concentration': str,  # 'HIGH' / 'MEDIUM' / 'LOW' / 'UNKNOWN'
            'data_available': bool
        }
    """
    try:
        # 提取供应量数据
        total_supply = coingecko_data.get("total_supply")
        circulating_supply = coingecko_data.get("circulating_supply")
        max_supply = coingecko_data.get("max_supply")
        
        logger.debug(
            f"Tokenomics 数据提取: total={total_supply}, "
            f"circulating={circulating_supply}, max={max_supply}"
        )
        
        # 检查数据可用性（至少需要 total_supply 或 circulating_supply）
        if total_supply is None and circulating_supply is None:
            logger.warning("Tokenomics 数据不可用：缺少供应量信息")
            return {
                "total_supply": None,
                "circulating_supply": None,
                "max_supply": None,
                "circulation_ratio": None,
                "has_max_supply": False,
                "is_deflationary": False,
                "supply_concentration": "UNKNOWN",
                "data_available": False
            }
        
        # 计算流通比例（注意除以 0 的防护）
        circulation_ratio = None
        if (
            circulating_supply is not None 
            and total_supply is not None 
            and total_supply > 0
        ):
            circulation_ratio = circulating_supply / total_supply
            logger.debug(f"流通比例计算: {circulation_ratio:.4f}")
        
        # 判断是否有最大供应量限制
        has_max_supply = max_supply is not None and max_supply > 0
        
        # 判断是否可能通缩（max_supply == total_supply 且两者都存在且大于 0）
        is_deflationary = False
        if (
            has_max_supply 
            and total_supply is not None 
            and total_supply > 0
            and max_supply == total_supply
        ):
            is_deflationary = True
            logger.debug("检测到可能的通缩模型：max_supply == total_supply")
        
        # 判断供应集中度
        # 基于流通比例判断：流通越少，集中度越高
        supply_concentration = _calculate_supply_concentration(circulation_ratio)
        
        token_name = coingecko_data.get("name", "Unknown")
        logger.info(
            f"Tokenomics 分析完成 [{token_name}]: "
            f"流通比例={circulation_ratio:.2%}" if circulation_ratio else f"流通比例=N/A"
        )
        
        return {
            "total_supply": total_supply,
            "circulating_supply": circulating_supply,
            "max_supply": max_supply,
            "circulation_ratio": circulation_ratio,
            "has_max_supply": has_max_supply,
            "is_deflationary": is_deflationary,
            "supply_concentration": supply_concentration,
            "data_available": True
        }
        
    except Exception as e:
        logger.error(f"Tokenomics 分析过程中发生错误: {e}", exc_info=True)
        return {
            "total_supply": None,
            "circulating_supply": None,
            "max_supply": None,
            "circulation_ratio": None,
            "has_max_supply": False,
            "is_deflationary": False,
            "supply_concentration": "UNKNOWN",
            "data_available": False
        }


def _calculate_supply_concentration(circulation_ratio: Optional[float]) -> str:
    """
    根据流通比例计算供应集中度
    
    流通比例越低，说明大部分代币未流通，集中度越高
    
    Args:
        circulation_ratio: 流通比例（0-1 之间）
    
    Returns:
        'HIGH' / 'MEDIUM' / 'LOW' / 'UNKNOWN'
    """
    if circulation_ratio is None:
        return "UNKNOWN"
    
    # 流通比例 < 20%：高集中度（砸盘风险高）
    if circulation_ratio < 0.2:
        return "HIGH"
    # 流通比例 20% - 50%：中等集中度
    elif circulation_ratio < 0.5:
        return "MEDIUM"
    # 流通比例 >= 50%：低集中度（分散持有）
    else:
        return "LOW"
