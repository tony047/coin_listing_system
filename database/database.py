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
            
            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_coin_id ON assessment_history(coin_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_created_at ON assessment_history(created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cache_expires ON data_cache(expires_at)")
            
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
