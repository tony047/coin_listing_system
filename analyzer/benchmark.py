"""
Token Lens 基准对标分析器
通过对比历史评估中的相似项目，为当前评估提供参照
"""
import json
import math
from typing import Dict, List, Any, Optional
from utils.logger import get_logger
from database import get_db

logger = get_logger()


class BenchmarkAnalyzer:
    """基准对标分析器，从历史评估记录中找到与当前 Token 相似的项目"""
    
    def __init__(self):
        self.db = get_db()
    
    def find_similar_projects(self, token_data: dict, limit: int = 5) -> List[Dict[str, Any]]:
        """
        找到历史上与当前 Token 相似的已评估项目
        
        相似性匹配策略：
        1. 市值排名在同一区间（±50%）
        2. 24h交易量在同一量级
        3. 交易所覆盖数量接近
        
        Args:
            token_data: 当前 Token 的数据字典
            limit: 返回的最大相似项目数量
            
        Returns:
            包含 coin_id, coin_name, total_score, verdict, similarity_score, created_at 的列表
        """
        try:
            current_coin_id = token_data.get("coin_id")
            
            # 获取历史评估记录（排除当前 Token）
            historical_records = self.db.get_similar_assessments(
                coin_id=current_coin_id,
                limit=100
            )
            
            if not historical_records:
                logger.info("没有可用的历史评估记录进行对标")
                return []
            
            # 计算每条记录的相似度
            similar_projects = []
            for record in historical_records:
                # 解析历史记录中的 token_data
                result_json = record.get("result_json")
                if not result_json:
                    continue
                
                # result_json 可能已经是 dict，也可能是 str
                if isinstance(result_json, str):
                    try:
                        result_json = json.loads(result_json)
                    except (json.JSONDecodeError, TypeError):
                        continue
                
                historical_token_data = result_json.get("token_data", {})
                
                # 计算相似度
                similarity = self._calculate_similarity(token_data, historical_token_data)
                
                similar_projects.append({
                    "coin_id": record.get("coin_id"),
                    "coin_name": record.get("coin_name"),
                    "coin_symbol": record.get("coin_symbol"),
                    "total_score": record.get("total_score"),
                    "verdict": record.get("verdict"),
                    "similarity_score": similarity,
                    "created_at": record.get("created_at"),
                    # 额外信息用于格式化
                    "market_cap_rank": historical_token_data.get("market_cap_rank"),
                })
            
            # 按相似度降序排序，取前 N 个
            similar_projects.sort(key=lambda x: x["similarity_score"], reverse=True)
            result = similar_projects[:limit]
            
            logger.info(f"找到 {len(result)} 个相似项目进行对标")
            return result
            
        except Exception as e:
            logger.error(f"查找相似项目时出错: {e}")
            return []
    
    def _calculate_similarity(self, current_data: dict, historical_data: dict) -> float:
        """
        计算两个 Token 的相似度（0-1）
        权重：市值排名40% + 交易量级30% + 交易所数量30%
        
        Args:
            current_data: 当前 Token 数据
            historical_data: 历史 Token 数据
            
        Returns:
            0-1 之间的相似度分数
        """
        # 市值排名相似度（权重 40%）
        rank1 = current_data.get("market_cap_rank")
        rank2 = historical_data.get("market_cap_rank")
        
        if rank1 is not None and rank2 is not None and rank1 > 0 and rank2 > 0:
            max_rank = max(rank1, rank2, 1)  # 防除以0
            rank_similarity = 1 - min(abs(rank1 - rank2) / max_rank, 1)
        else:
            rank_similarity = 0.5  # 缺失数据时使用中立值
        
        # 交易量级相似度（权重 30%）- 使用对数比较量级
        vol1 = current_data.get("volume_24h_usd")
        vol2 = historical_data.get("volume_24h_usd")
        
        if vol1 is not None and vol2 is not None and vol1 > 0 and vol2 > 0:
            try:
                log_diff = abs(math.log10(vol1) - math.log10(vol2))
                volume_similarity = 1 - min(log_diff / 3, 1)  # 3个数量级差距视为完全不相似
            except (ValueError, ZeroDivisionError):
                volume_similarity = 0.5
        else:
            volume_similarity = 0.5  # 缺失数据时使用中立值
        
        # 交易所数量相似度（权重 30%）
        # 从 listed_on_major 列表长度获取交易所数量
        count1 = len(current_data.get("listed_on_major", [])) if current_data.get("listed_on_major") else None
        count2 = len(historical_data.get("listed_on_major", [])) if historical_data.get("listed_on_major") else None
        
        # 如果没有 listed_on_major，尝试用 exchange_count 字段
        if count1 is None:
            count1 = current_data.get("exchange_count")
        if count2 is None:
            count2 = historical_data.get("exchange_count")
        
        if count1 is not None and count2 is not None:
            max_count = max(count1, count2, 1)  # 防除以0
            exchange_similarity = 1 - min(abs(count1 - count2) / max_count, 1)
        else:
            exchange_similarity = 0.5  # 缺失数据时使用中立值
        
        # 加权平均计算总相似度
        total_similarity = (
            rank_similarity * 0.4 +
            volume_similarity * 0.3 +
            exchange_similarity * 0.3
        )
        
        return round(total_similarity, 3)
    
    def format_benchmark_for_prompt(self, similar_projects: list) -> str:
        """
        将基准对标结果格式化为 Claude prompt 文本
        
        Args:
            similar_projects: find_similar_projects 返回的相似项目列表
            
        Returns:
            格式化的对比信息字符串，如果没有相似项目返回空字符串
        """
        if not similar_projects:
            return ""
        
        lines = ["以下是与该项目最相似的历史评估项目对比：", ""]
        
        for i, project in enumerate(similar_projects, 1):
            coin_name = project.get("coin_name", "Unknown")
            coin_symbol = project.get("coin_symbol", "")
            similarity = project.get("similarity_score", 0)
            total_score = project.get("total_score", 0)
            verdict = project.get("verdict", "未知")
            market_cap_rank = project.get("market_cap_rank")
            created_at = project.get("created_at", "")
            
            # 格式化相似度为百分比
            similarity_pct = int(similarity * 100)
            
            # 构建项目对比信息
            symbol_str = f" ({coin_symbol})" if coin_symbol else ""
            lines.append(f"{i}. {coin_name}{symbol_str} - 相似度 {similarity_pct}%")
            lines.append(f"   - 评估评分：{total_score}/100（结论：{verdict}）")
            
            if market_cap_rank:
                lines.append(f"   - 市值排名：#{market_cap_rank}")
            
            # 格式化评估时间
            if created_at:
                # 只取日期部分
                date_str = str(created_at)[:10] if len(str(created_at)) >= 10 else created_at
                lines.append(f"   - 评估时间：{date_str}")
            
            lines.append("")  # 空行分隔
        
        return "\n".join(lines).rstrip()


def find_benchmarks(token_data: dict, limit: int = 5) -> tuple:
    """
    便捷函数：获取基准对标结果和格式化文本
    
    Args:
        token_data: 当前 Token 的数据字典
        limit: 返回的最大相似项目数量
        
    Returns:
        (similar_projects_list, formatted_prompt_text) 元组
    """
    analyzer = BenchmarkAnalyzer()
    similar = analyzer.find_similar_projects(token_data, limit)
    prompt_text = analyzer.format_benchmark_for_prompt(similar)
    return similar, prompt_text
