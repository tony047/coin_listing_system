"""
SQLite 数据库实现
用于历史记录持久化和数据缓存
"""

import sqlite3
import json
import os
import time
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager


class Database:
    """SQLite 数据库管理类"""
    
    def __init__(self, db_path: str = "data/token_lens.db"):
        """
        初始化数据库
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        # 确保数据目录存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_tables()
    
    def _init_tables(self):
        """初始化数据库表"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 历史记录表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS assessment_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    coin_id TEXT NOT NULL,
                    coin_name TEXT NOT NULL,
                    coin_symbol TEXT NOT NULL,
                    total_score INTEGER NOT NULL,
                    verdict TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(coin_id, created_at)
                )
            """)
            
            # 数据缓存表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS data_cache (
                    cache_key TEXT PRIMARY KEY,
                    cache_data TEXT NOT NULL,
                    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP
                )
            """)
            
            # 批量评估任务表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS batch_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_name TEXT NOT NULL,
                    total_count INTEGER NOT NULL,
                    completed_count INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 批量评估结果表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS batch_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    coin_id TEXT NOT NULL,
                    coin_name TEXT,
                    status TEXT DEFAULT 'pending',
                    result_json TEXT,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES batch_tasks(id)
                )
            """)
            
            # 预测跟踪表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS prediction_tracking (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    assessment_id INTEGER NOT NULL,
                    coin_id TEXT NOT NULL,
                    coin_name TEXT,
                    predicted_score INTEGER,
                    predicted_verdict TEXT,
                    actual_return_30d FLOAT,
                    actual_return_90d FLOAT,
                    actual_verdict TEXT,
                    is_accurate BOOLEAN,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    verified_at TIMESTAMP,
                    FOREIGN KEY (assessment_id) REFERENCES assessment_history(id)
                )
            """)
            
            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_coin_id ON assessment_history(coin_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_created_at ON assessment_history(created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cache_expires ON data_cache(expires_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_prediction_coin_id ON prediction_tracking(coin_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_prediction_verified ON prediction_tracking(verified_at)")
            
            conn.commit()
    
    @contextmanager
    def _get_connection(self):
        """获取数据库连接上下文管理器"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    # ========== 历史记录操作 ==========
    
    def save_assessment(self, coin_id: str, coin_name: str, coin_symbol: str,
                        total_score: int, verdict: str, result: dict) -> int:
        """
        保存评估记录
        
        Args:
            coin_id: CoinGecko coin ID
            coin_name: Token 名称
            coin_symbol: Token 符号
            total_score: 总分
            verdict: 评估结论
            result: 完整评估结果
            
        Returns:
            记录ID
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO assessment_history 
                (coin_id, coin_name, coin_symbol, total_score, verdict, result_json)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (coin_id, coin_name, coin_symbol, total_score, verdict, json.dumps(result)))
            conn.commit()
            return cursor.lastrowid
    
    def get_history(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        获取历史记录列表
        
        Args:
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            历史记录列表
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, coin_id, coin_name, coin_symbol, total_score, 
                       verdict, created_at
                FROM assessment_history
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_assessment_by_id(self, record_id: int) -> Optional[Dict[str, Any]]:
        """
        根据ID获取评估记录详情
        
        Args:
            record_id: 记录ID
            
        Returns:
            评估记录详情
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM assessment_history WHERE id = ?
            """, (record_id,))
            row = cursor.fetchone()
            if row:
                result = dict(row)
                result['result_json'] = json.loads(result['result_json'])
                return result
            return None
    
    def get_assessment_by_coin_id(self, coin_id: str) -> Optional[Dict[str, Any]]:
        """
        根据coin_id获取最近的评估记录
        
        Args:
            coin_id: CoinGecko coin ID
            
        Returns:
            评估记录详情
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM assessment_history 
                WHERE coin_id = ? 
                ORDER BY created_at DESC 
                LIMIT 1
            """, (coin_id,))
            row = cursor.fetchone()
            if row:
                result = dict(row)
                result['result_json'] = json.loads(result['result_json'])
                return result
            return None
    
    def delete_assessment(self, record_id: int) -> bool:
        """
        删除评估记录
        
        Args:
            record_id: 记录ID
            
        Returns:
            是否删除成功
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM assessment_history WHERE id = ?", (record_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def get_history_count(self) -> int:
        """获取历史记录总数"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM assessment_history")
            return cursor.fetchone()[0]
    
    # ========== 缓存操作 ==========
    
    def get_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        获取缓存数据
        
        Args:
            cache_key: 缓存键
            
        Returns:
            缓存数据，不存在或已过期返回None
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT cache_data, expires_at FROM data_cache 
                WHERE cache_key = ?
            """, (cache_key,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            # 检查是否过期
            if row['expires_at']:
                try:
                    expires_at = float(row['expires_at'])
                    if time.time() > expires_at:
                        # 删除过期缓存
                        cursor.execute("DELETE FROM data_cache WHERE cache_key = ?", (cache_key,))
                        conn.commit()
                        return None
                except (ValueError, TypeError):
                    pass  # 无效的过期时间，忽略
            
            return json.loads(row['cache_data'])
    
    def set_cache(self, cache_key: str, cache_data: Dict[str, Any], 
                  ttl_seconds: Optional[int] = None) -> None:
        """
        设置缓存数据
        
        Args:
            cache_key: 缓存键
            cache_data: 缓存数据
            ttl_seconds: 过期时间（秒），None表示永不过期
        """
        expires_at = None
        if ttl_seconds:
            expires_at = (datetime.now().timestamp() + ttl_seconds)
            
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO data_cache 
                (cache_key, cache_data, expires_at)
                VALUES (?, ?, ?)
            """, (cache_key, json.dumps(cache_data), expires_at))
            conn.commit()
    
    def clear_expired_cache(self) -> int:
        """
        清除过期缓存
        
        Returns:
            删除的缓存数量
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM data_cache 
                WHERE expires_at IS NOT NULL 
                AND expires_at < ?
            """, (datetime.now().timestamp(),))
            conn.commit()
            return cursor.rowcount
    
    # ========== 批量评估操作 ==========
    
    def create_batch_task(self, task_name: str, coin_ids: List[str]) -> int:
        """
        创建批量评估任务
        
        Args:
            task_name: 任务名称
            coin_ids: 要评估的coin_id列表
            
        Returns:
            任务ID
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 创建任务
            cursor.execute("""
                INSERT INTO batch_tasks (task_name, total_count)
                VALUES (?, ?)
            """, (task_name, len(coin_ids)))
            task_id = cursor.lastrowid
            
            # 创建评估记录
            for coin_id in coin_ids:
                cursor.execute("""
                    INSERT INTO batch_results (task_id, coin_id)
                    VALUES (?, ?)
                """, (task_id, coin_id))
            
            conn.commit()
            return task_id
    
    def update_batch_result(self, task_id: int, coin_id: str, 
                           status: str, result: Optional[dict] = None,
                           error_message: Optional[str] = None) -> None:
        """
        更新批量评估结果
        
        Args:
            task_id: 任务ID
            coin_id: CoinGecko coin ID
            status: 状态 (completed/failed)
            result: 评估结果
            error_message: 错误信息
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 更新结果
            cursor.execute("""
                UPDATE batch_results 
                SET status = ?, result_json = ?, error_message = ?
                WHERE task_id = ? AND coin_id = ?
            """, (status, json.dumps(result) if result else None, 
                  error_message, task_id, coin_id))
            
            # 更新任务进度
            cursor.execute("""
                UPDATE batch_tasks 
                SET completed_count = completed_count + 1,
                    status = CASE 
                        WHEN completed_count + 1 >= total_count THEN 'completed'
                        ELSE 'running'
                    END
                WHERE id = ?
            """, (task_id,))
            
            conn.commit()
    
    def get_batch_task(self, task_id: int) -> Optional[Dict[str, Any]]:
        """
        获取批量评估任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务信息
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM batch_tasks WHERE id = ?
            """, (task_id,))
            return dict(cursor.fetchone()) if cursor.fetchone() else None
    
    def get_batch_results(self, task_id: int) -> List[Dict[str, Any]]:
        """
        获取批量评估结果
        
        Args:
            task_id: 任务ID
            
        Returns:
            结果列表
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM batch_results WHERE task_id = ?
            """, (task_id,))
            
            results = []
            for row in cursor.fetchall():
                result = dict(row)
                if result['result_json']:
                    result['result_json'] = json.loads(result['result_json'])
                results.append(result)
            return results
    
    # ========== 预测跟踪操作 ==========
    
    def save_prediction(self, assessment_id: int, coin_id: str, coin_name: str,
                        predicted_score: int, predicted_verdict: str) -> int:
        """
        保存预测记录
        
        Args:
            assessment_id: 关联的评估记录ID
            coin_id: CoinGecko coin ID
            coin_name: Token 名称
            predicted_score: 预测分数
            predicted_verdict: 预测结论
            
        Returns:
            预测ID
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO prediction_tracking 
                    (assessment_id, coin_id, coin_name, predicted_score, predicted_verdict)
                    VALUES (?, ?, ?, ?, ?)
                """, (assessment_id, coin_id, coin_name, predicted_score, predicted_verdict))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            raise RuntimeError(f"保存预测记录失败：{e}")
    
    def update_actual_performance(self, prediction_id: int, 
                                   actual_return_30d: float = None,
                                   actual_return_90d: float = None) -> bool:
        """
        更新实际表现数据
        
        根据实际回报判断 actual_verdict:
        - return_30d > 20%: "强烈推荐" 正确
        - return_30d between -30% and 20%: "建议观望" 正确
        - return_30d < -30%: "不建议上币" 正确
        
        Args:
            prediction_id: 预测记录ID
            actual_return_30d: 30天实际回报率（百分比）
            actual_return_90d: 90天实际回报率（百分比）
            
        Returns:
            是否更新成功
        """
        try:
            # 获取当前预测记录
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT predicted_verdict FROM prediction_tracking WHERE id = ?
                """, (prediction_id,))
                row = cursor.fetchone()
                if not row:
                    return False
                
                predicted_verdict = row['predicted_verdict']
                
                # 根据30天回报确定实际结论
                actual_verdict = None
                if actual_return_30d is not None:
                    if actual_return_30d > 20:
                        actual_verdict = "强烈推荐"
                    elif actual_return_30d < -30:
                        actual_verdict = "不建议上币"
                    else:
                        actual_verdict = "建议观望"
                
                # 判断预测是否准确
                is_accurate = None
                if actual_verdict and predicted_verdict:
                    is_accurate = (predicted_verdict == actual_verdict)
                
                # 更新记录
                cursor.execute("""
                    UPDATE prediction_tracking 
                    SET actual_return_30d = ?,
                        actual_return_90d = ?,
                        actual_verdict = ?,
                        is_accurate = ?,
                        verified_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (actual_return_30d, actual_return_90d, actual_verdict, is_accurate, prediction_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            raise RuntimeError(f"更新实际表现失败：{e}")
    
    def calculate_accuracy(self) -> dict:
        """
        计算预测准确率
        
        Returns:
            {
                'total_predictions': int,
                'verified_predictions': int,
                'accuracy': float,  # 0-1
                'precision_by_verdict': {
                    '强烈推荐': {'correct': int, 'total': int, 'precision': float},
                    '建议观望': {...},
                    '不建议上币': {...}
                },
                'confusion_matrix': dict
            }
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # 获取总预测数
                cursor.execute("SELECT COUNT(*) FROM prediction_tracking")
                total_predictions = cursor.fetchone()[0]
                
                # 获取已验证预测数
                cursor.execute("SELECT COUNT(*) FROM prediction_tracking WHERE verified_at IS NOT NULL")
                verified_predictions = cursor.fetchone()[0]
                
                # 获取准确预测数
                cursor.execute("SELECT COUNT(*) FROM prediction_tracking WHERE is_accurate = 1")
                accurate_count = cursor.fetchone()[0]
                
                # 计算总体准确率
                accuracy = accurate_count / verified_predictions if verified_predictions > 0 else 0.0
                
                # 按预测结论统计准确率
                verdicts = ['强烈推荐', '建议观望', '不建议上币']
                precision_by_verdict = {}
                
                for verdict in verdicts:
                    cursor.execute("""
                        SELECT COUNT(*) FROM prediction_tracking 
                        WHERE predicted_verdict = ? AND verified_at IS NOT NULL
                    """, (verdict,))
                    total = cursor.fetchone()[0]
                    
                    cursor.execute("""
                        SELECT COUNT(*) FROM prediction_tracking 
                        WHERE predicted_verdict = ? AND is_accurate = 1
                    """, (verdict,))
                    correct = cursor.fetchone()[0]
                    
                    precision_by_verdict[verdict] = {
                        'correct': correct,
                        'total': total,
                        'precision': correct / total if total > 0 else 0.0
                    }
                
                # 构建混淆矩阵
                confusion_matrix = {}
                for predicted in verdicts:
                    confusion_matrix[predicted] = {}
                    for actual in verdicts:
                        cursor.execute("""
                            SELECT COUNT(*) FROM prediction_tracking 
                            WHERE predicted_verdict = ? AND actual_verdict = ?
                        """, (predicted, actual))
                        confusion_matrix[predicted][actual] = cursor.fetchone()[0]
                
                return {
                    'total_predictions': total_predictions,
                    'verified_predictions': verified_predictions,
                    'accuracy': accuracy,
                    'precision_by_verdict': precision_by_verdict,
                    'confusion_matrix': confusion_matrix
                }
        except Exception as e:
            raise RuntimeError(f"计算准确率失败：{e}")
    
    def get_unverified_predictions(self, min_age_days: int = 30) -> list:
        """
        获取超过指定天数但未验证的预测记录
        
        Args:
            min_age_days: 最小天数阈值
            
        Returns:
            未验证的预测记录列表
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT pt.*, ah.result_json
                    FROM prediction_tracking pt
                    LEFT JOIN assessment_history ah ON pt.assessment_id = ah.id
                    WHERE pt.verified_at IS NULL 
                    AND pt.created_at <= datetime('now', ?)
                    ORDER BY pt.created_at ASC
                """, (f'-{min_age_days} days',))
                
                results = []
                for row in cursor.fetchall():
                    result = dict(row)
                    if result.get('result_json'):
                        result['result_json'] = json.loads(result['result_json'])
                    results.append(result)
                return results
        except Exception as e:
            raise RuntimeError(f"获取未验证预测失败：{e}")
    
    def get_prediction_stats(self) -> dict:
        """
        获取预测统计概览（供诊断面板使用）
        
        Returns:
            {
                'total_predictions': int,
                'verified_count': int,
                'pending_count': int,
                'accuracy_rate': float,
                'by_verdict': dict,
                'recent_predictions': list
            }
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # 基础统计
                cursor.execute("SELECT COUNT(*) FROM prediction_tracking")
                total = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM prediction_tracking WHERE verified_at IS NOT NULL")
                verified = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM prediction_tracking WHERE verified_at IS NULL")
                pending = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM prediction_tracking WHERE is_accurate = 1")
                accurate = cursor.fetchone()[0]
                
                accuracy_rate = accurate / verified if verified > 0 else 0.0
                
                # 按预测结论统计
                cursor.execute("""
                    SELECT predicted_verdict, COUNT(*) as count 
                    FROM prediction_tracking 
                    GROUP BY predicted_verdict
                """)
                by_verdict = {row['predicted_verdict']: row['count'] for row in cursor.fetchall()}
                
                # 最近预测
                cursor.execute("""
                    SELECT id, coin_id, coin_name, predicted_score, predicted_verdict, 
                           actual_verdict, is_accurate, created_at, verified_at
                    FROM prediction_tracking
                    ORDER BY created_at DESC
                    LIMIT 10
                """)
                recent = [dict(row) for row in cursor.fetchall()]
                
                return {
                    'total_predictions': total,
                    'verified_count': verified,
                    'pending_count': pending,
                    'accuracy_rate': accuracy_rate,
                    'by_verdict': by_verdict,
                    'recent_predictions': recent
                }
        except Exception as e:
            raise RuntimeError(f"获取预测统计失败：{e}")
    
    def get_failed_predictions(self) -> list:
        """
        获取所有预测失败的记录（用于权重分析）
        
        Returns:
            预测失败的记录列表（包含关联的评估结果）
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT pt.*, ah.result_json
                    FROM prediction_tracking pt
                    LEFT JOIN assessment_history ah ON pt.assessment_id = ah.id
                    WHERE pt.is_accurate = 0
                    ORDER BY pt.verified_at DESC
                """)
                
                results = []
                for row in cursor.fetchall():
                    result = dict(row)
                    if result.get('result_json'):
                        result['result_json'] = json.loads(result['result_json'])
                    results.append(result)
                return results
        except Exception as e:
            raise RuntimeError(f"获取失败预测失败：{e}")
    
    # ========== 基准对标操作 ==========
    
    def get_similar_assessments(self, coin_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取用于基准对标的历史评估记录（排除指定 coin_id）
        
        Args:
            coin_id: 需要排除的 CoinGecko coin ID（当前正在评估的 Token）
            limit: 返回数量限制
            
        Returns:
            包含 result_json 的完整评估记录列表
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                if coin_id:
                    cursor.execute("""
                        SELECT id, coin_id, coin_name, coin_symbol, total_score, 
                               verdict, result_json, created_at
                        FROM assessment_history
                        WHERE coin_id != ?
                        ORDER BY created_at DESC
                        LIMIT ?
                    """, (coin_id, limit))
                else:
                    cursor.execute("""
                        SELECT id, coin_id, coin_name, coin_symbol, total_score, 
                               verdict, result_json, created_at
                        FROM assessment_history
                        ORDER BY created_at DESC
                        LIMIT ?
                    """, (limit,))
                
                results = []
                for row in cursor.fetchall():
                    result = dict(row)
                    # result_json 保持为字符串，由调用方解析
                    results.append(result)
                return results
        except Exception as e:
            raise RuntimeError(f"获取历史评估记录失败：{e}")


# 全局数据库实例
_db_instance: Optional[Database] = None


def init_db(db_path: str = "data/token_lens.db") -> Database:
    """
    初始化数据库
    
    Args:
        db_path: 数据库文件路径
        
    Returns:
        数据库实例
    """
    global _db_instance
    _db_instance = Database(db_path)
    return _db_instance


def get_db() -> Database:
    """
    获取数据库实例
    
    Returns:
        数据库实例
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance
