"""
Token Lens 回测引擎
用于验证历史预测的准确性并优化评分权重
"""

import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

try:
    from ..utils.logger import get_logger
except ImportError:
    from utils.logger import get_logger

try:
    from ..database import get_db
except ImportError:
    from database import get_db

try:
    from ..collectors.coingecko import get_token_data
except ImportError:
    from collectors.coingecko import get_token_data

logger = get_logger()


class BacktestEngine:
    """回测引擎"""
    
    # 默认权重配置
    DEFAULT_WEIGHTS = {
        'market': 25,
        'community': 15,
        'technical': 15,
        'competitive': 15,
        'risk': 10,
        'tokenomics': 10,
        'onchain': 10
    }
    
    def __init__(self):
        """初始化回测引擎"""
        self.db = get_db()
        self._last_backtest_time: Optional[str] = None
    
    def run_backtest(self, max_records: int = 100) -> Dict[str, Any]:
        """
        运行回测：遍历历史评估，获取当前价格计算实际回报
        
        逻辑：
        1. 获取所有未验证且创建超过30天的预测记录
        2. 对每条记录，从 CoinGecko 获取当前价格
        3. 与评估时的价格对比，计算回报率
        4. 更新 prediction_tracking 表
        5. 返回汇总统计
        
        注意：
        - CoinGecko API 有频率限制，每次回测间隔至少 2 秒
        - 如果获取价格失败，跳过该记录
        - 返回成功和失败的计数
        
        Args:
            max_records: 最大处理记录数
            
        Returns:
            回测结果统计
        """
        logger.info(f"开始回测，最大处理记录数: {max_records}")
        
        results = {
            'processed': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'errors': [],
            'updated_records': []
        }
        
        try:
            # 获取未验证的预测记录
            unverified = self.db.get_unverified_predictions(min_age_days=30)
            
            if not unverified:
                logger.info("没有需要验证的预测记录")
                results['message'] = "没有需要验证的预测记录"
                return results
            
            # 限制处理数量
            records_to_process = unverified[:max_records]
            logger.info(f"找到 {len(unverified)} 条未验证记录，将处理 {len(records_to_process)} 条")
            
            for record in records_to_process:
                results['processed'] += 1
                prediction_id = record['id']
                coin_id = record['coin_id']
                
                try:
                    # CoinGecko API 频率限制
                    time.sleep(2)
                    
                    # 获取当前价格数据
                    current_data = get_token_data(coin_id)
                    current_price = current_data.get('price_usd')
                    
                    if current_price is None:
                        logger.warning(f"无法获取 {coin_id} 的当前价格")
                        results['skipped'] += 1
                        continue
                    
                    # 从评估结果中获取评估时的价格
                    result_json = record.get('result_json', {})
                    
                    # 尝试从不同位置获取原始价格
                    original_price = None
                    if isinstance(result_json, dict):
                        # 尝试从 market_data 获取
                        market_data = result_json.get('market_data', {})
                        if isinstance(market_data, dict):
                            original_price = market_data.get('price_usd')
                        
                        # 如果还是没有，尝试从 raw_data 获取
                        if original_price is None:
                            raw_data = result_json.get('raw_data', {})
                            if isinstance(raw_data, dict):
                                original_price = raw_data.get('price_usd')
                    
                    if original_price is None or original_price == 0:
                        logger.warning(f"无法获取 {coin_id} 的原始价格")
                        results['skipped'] += 1
                        continue
                    
                    # 计算回报率（百分比）
                    return_30d = ((current_price - original_price) / original_price) * 100
                    
                    # 更新数据库
                    success = self.db.update_actual_performance(
                        prediction_id=prediction_id,
                        actual_return_30d=return_30d
                    )
                    
                    if success:
                        results['success'] += 1
                        results['updated_records'].append({
                            'prediction_id': prediction_id,
                            'coin_id': coin_id,
                            'original_price': original_price,
                            'current_price': current_price,
                            'return_30d': return_30d
                        })
                        logger.info(f"更新 {coin_id} 回报率: {return_30d:.2f}%")
                    else:
                        results['failed'] += 1
                        
                except RuntimeError as e:
                    error_msg = f"处理 {coin_id} 失败: {str(e)}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)
                    results['failed'] += 1
                except Exception as e:
                    error_msg = f"处理 {coin_id} 时发生未知错误: {str(e)}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)
                    results['failed'] += 1
            
            # 记录回测时间
            self._last_backtest_time = datetime.now().isoformat()
            
            logger.info(f"回测完成: 处理 {results['processed']} 条, "
                       f"成功 {results['success']} 条, 失败 {results['failed']} 条")
            
        except Exception as e:
            error_msg = f"回测过程中发生错误: {str(e)}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
        
        return results
    
    def calculate_accuracy(self) -> Dict[str, Any]:
        """
        计算整体预测准确率
        调用 db.calculate_accuracy() 并格式化结果
        
        Returns:
            格式化的准确率统计
        """
        try:
            accuracy_data = self.db.calculate_accuracy()
            
            # 格式化结果
            formatted = {
                'summary': {
                    'total_predictions': accuracy_data['total_predictions'],
                    'verified_predictions': accuracy_data['verified_predictions'],
                    'accuracy_percentage': round(accuracy_data['accuracy'] * 100, 2),
                    'accuracy_grade': self._get_accuracy_grade(accuracy_data['accuracy'])
                },
                'by_verdict': {},
                'confusion_matrix': accuracy_data['confusion_matrix']
            }
            
            # 格式化各结论的准确率
            for verdict, data in accuracy_data['precision_by_verdict'].items():
                formatted['by_verdict'][verdict] = {
                    'correct': data['correct'],
                    'total': data['total'],
                    'precision_percentage': round(data['precision'] * 100, 2)
                }
            
            return formatted
            
        except Exception as e:
            logger.error(f"计算准确率失败: {str(e)}")
            raise RuntimeError(f"计算准确率失败: {str(e)}")
    
    def _get_accuracy_grade(self, accuracy: float) -> str:
        """
        根据准确率返回等级评价
        
        Args:
            accuracy: 准确率 (0-1)
            
        Returns:
            等级评价
        """
        if accuracy >= 0.8:
            return "优秀"
        elif accuracy >= 0.6:
            return "良好"
        elif accuracy >= 0.4:
            return "一般"
        else:
            return "需改进"
    
    def suggest_weight_adjustments(self) -> Dict[str, Any]:
        """
        基于失败案例分析权重偏差
        
        逻辑：
        1. 获取所有 is_accurate=False 的记录
        2. 从 assessment_history 获取对应的 result_json
        3. 分析失败案例中各维度评分的偏差模式
        4. 返回建议的权重调整
        
        Returns:
            {
                'sample_size': int,
                'failure_patterns': [
                    {
                        'dimension': 'market',
                        'avg_score_in_failures': 22.5,
                        'avg_score_overall': 20.0,
                        'suggestion': '市场维度在失败案例中得分偏高，建议降低权重'
                    }
                ],
                'suggested_weights': {
                    'market': 25,
                    'community': 15,
                    'technical': 15,
                    'competitive': 15,
                    'risk': 10,
                    'tokenomics': 10,
                    'onchain': 10
                }
            }
        """
        try:
            # 获取失败的预测记录
            failed_predictions = self.db.get_failed_predictions()
            
            if not failed_predictions:
                return {
                    'sample_size': 0,
                    'failure_patterns': [],
                    'suggested_weights': self.DEFAULT_WEIGHTS.copy(),
                    'message': '没有失败案例可供分析'
                }
            
            # 维度列表
            dimensions = ['market', 'community', 'technical', 'competitive', 
                         'risk', 'tokenomics', 'onchain']
            
            # 统计失败案例中各维度的分数
            failure_scores = {dim: [] for dim in dimensions}
            
            for record in failed_predictions:
                result_json = record.get('result_json', {})
                if not isinstance(result_json, dict):
                    continue
                
                # 从 dimensions 或 scores 字段提取分数
                scores = result_json.get('dimensions', result_json.get('scores', {}))
                if isinstance(scores, dict):
                    for dim in dimensions:
                        dim_data = scores.get(dim, {})
                        if isinstance(dim_data, dict):
                            score = dim_data.get('score', dim_data.get('value'))
                            if score is not None:
                                failure_scores[dim].append(score)
                        elif isinstance(dim_data, (int, float)):
                            failure_scores[dim].append(dim_data)
            
            # 分析偏差模式
            failure_patterns = []
            suggested_weights = self.DEFAULT_WEIGHTS.copy()
            
            for dim in dimensions:
                scores = failure_scores[dim]
                if not scores:
                    continue
                
                avg_failure_score = sum(scores) / len(scores)
                default_weight = self.DEFAULT_WEIGHTS.get(dim, 15)
                
                # 计算偏差
                # 如果失败案例中该维度得分偏高，说明可能高估了该维度的重要性
                pattern = {
                    'dimension': dim,
                    'avg_score_in_failures': round(avg_failure_score, 2),
                    'sample_count': len(scores),
                    'current_weight': default_weight
                }
                
                # 根据偏差程度给出建议
                # 假设正常情况下各维度得分应该在其权重范围内
                expected_score = default_weight * 0.7  # 预期得分约为权重的70%
                
                if avg_failure_score > expected_score * 1.3:
                    # 失败案例中得分偏高
                    suggested_adjustment = max(5, default_weight - 5)
                    pattern['suggestion'] = f'{self._get_dim_name(dim)}在失败案例中得分偏高，建议降低权重'
                    pattern['suggested_weight'] = suggested_adjustment
                    suggested_weights[dim] = suggested_adjustment
                elif avg_failure_score < expected_score * 0.7:
                    # 失败案例中得分偏低
                    suggested_adjustment = min(30, default_weight + 5)
                    pattern['suggestion'] = f'{self._get_dim_name(dim)}在失败案例中得分偏低，建议提高权重'
                    pattern['suggested_weight'] = suggested_adjustment
                    suggested_weights[dim] = suggested_adjustment
                else:
                    pattern['suggestion'] = f'{self._get_dim_name(dim)}得分正常，建议保持当前权重'
                    pattern['suggested_weight'] = default_weight
                
                failure_patterns.append(pattern)
            
            # 归一化权重，确保总和为100
            total_weight = sum(suggested_weights.values())
            if total_weight > 0:
                factor = 100 / total_weight
                suggested_weights = {k: round(v * factor) for k, v in suggested_weights.items()}
            
            return {
                'sample_size': len(failed_predictions),
                'failure_patterns': failure_patterns,
                'suggested_weights': suggested_weights
            }
            
        except Exception as e:
            logger.error(f"分析权重偏差失败: {str(e)}")
            raise RuntimeError(f"分析权重偏差失败: {str(e)}")
    
    def _get_dim_name(self, dim: str) -> str:
        """
        获取维度的中文名称
        
        Args:
            dim: 维度英文名
            
        Returns:
            中文名称
        """
        dim_names = {
            'market': '市场',
            'community': '社区',
            'technical': '技术',
            'competitive': '竞争',
            'risk': '风险',
            'tokenomics': '代币经济',
            'onchain': '链上'
        }
        return dim_names.get(dim, dim)
    
    def get_backtest_summary(self) -> Dict[str, Any]:
        """
        获取回测汇总信息（供 UI 展示）
        
        Returns:
            {
                'last_backtest_time': str or None,
                'total_predictions': int,
                'verified_count': int,
                'accuracy_metrics': dict,
                'weight_suggestions': dict
            }
        """
        try:
            # 获取预测统计
            stats = self.db.get_prediction_stats()
            
            # 计算准确率指标
            accuracy_metrics = None
            if stats['verified_count'] > 0:
                accuracy_metrics = self.calculate_accuracy()
            
            # 获取权重建议
            weight_suggestions = None
            try:
                weight_suggestions = self.suggest_weight_adjustments()
            except Exception:
                pass  # 如果没有足够数据，忽略
            
            return {
                'last_backtest_time': self._last_backtest_time,
                'total_predictions': stats['total_predictions'],
                'verified_count': stats['verified_count'],
                'pending_count': stats['pending_count'],
                'accuracy_metrics': accuracy_metrics,
                'weight_suggestions': weight_suggestions,
                'recent_predictions': stats['recent_predictions']
            }
            
        except Exception as e:
            logger.error(f"获取回测汇总失败: {str(e)}")
            raise RuntimeError(f"获取回测汇总失败: {str(e)}")


# 便捷函数
def run_backtest(max_records: int = 100) -> Dict[str, Any]:
    """
    运行回测的便捷函数
    
    Args:
        max_records: 最大处理记录数
        
    Returns:
        回测结果
    """
    engine = BacktestEngine()
    return engine.run_backtest(max_records)


def get_accuracy() -> Dict[str, Any]:
    """
    获取准确率的便捷函数
    
    Returns:
        准确率统计
    """
    engine = BacktestEngine()
    return engine.calculate_accuracy()


def get_weight_suggestions() -> Dict[str, Any]:
    """
    获取权重建议的便捷函数
    
    Returns:
        权重建议
    """
    engine = BacktestEngine()
    return engine.suggest_weight_adjustments()
