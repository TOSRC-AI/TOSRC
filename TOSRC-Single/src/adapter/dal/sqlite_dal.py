"""
单租户SQLite数据访问层实现
实现TOSRC-Core定义的BaseDAL接口，基于现有bionic_db封装

优化：使用连接池提升高并发性能
"""
import sqlite3
import os
import logging
from typing import List, Dict, Any, Optional
from tosrc_core.common.interface.dal import BaseDAL
from src.common.exceptions import DatabaseException, NotFoundException, DuplicateException
from src.common.error_codes import ErrorCode
from .connection_pool import get_connection_pool, PoolConfig

logger = logging.getLogger(__name__)


class SQLiteDAL(BaseDAL):
    """SQLite数据访问层实现（支持连接池）"""

    def __init__(self, db_path: str, use_pool: bool = True, pool_config: Optional[PoolConfig] = None):
        """
        初始化SQLite DAL

        Args:
            db_path: 数据库文件路径
            use_pool: 是否使用连接池
            pool_config: 连接池配置
        """
        self.db_path = db_path
        self.use_pool = use_pool

        # 确保目录存在
        try:
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
        except OSError as e:
            raise DatabaseException(
                error_code=ErrorCode.DB_ERROR,
                detail=f"创建数据库目录失败: {e}",
                cause=e
            ) from e

        # 事务连接，开启事务时使用
        self._transaction_conn = None

        # 连接池
        self._pool = None
        if use_pool:
            self._pool = get_connection_pool(db_path, pool_config)
            logger.info(f"SQLiteDAL 使用连接池: {db_path}")

    def get_connection(self, write: bool = False):
        """获取数据库连接"""
        # 如果在事务中，直接返回事务连接
        if self._transaction_conn is not None:
            return self._transaction_conn

        # 使用连接池或创建新连接
        if self.use_pool and self._pool:
            return self._pool.get_connection()

        # 回退到直接创建连接
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    # ===== 通用SQL操作接口实现 =====
    def execute_query(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """执行查询SQL，返回结果列表"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            # 连接池会自动处理归还；事务连接不关闭
            if not self.use_pool and self._transaction_conn is None and hasattr(conn, 'close'):
                conn.close()
    
    def execute_insert(self, sql: str, params: tuple = ()) -> int:
        """执行插入SQL，返回自增ID"""
        conn = self.get_connection(write=True)
        try:
            cursor = conn.cursor()
            cursor.execute(sql, params)

            # 非事务模式自动提交
            if self._transaction_conn is None:
                conn.commit()

            return cursor.lastrowid
        finally:
            if not self.use_pool and self._transaction_conn is None and hasattr(conn, 'close'):
                conn.close()

    def execute_update(self, sql: str, params: tuple = ()) -> bool:
        """执行更新/删除SQL，返回是否成功"""
        conn = self.get_connection(write=True)
        try:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            affected = cursor.rowcount > 0

            # 非事务模式自动提交
            if self._transaction_conn is None:
                conn.commit()

            return affected
        finally:
            if not self.use_pool and self._transaction_conn is None and hasattr(conn, 'close'):
                conn.close()
    
    # ===== 事务接口实现 =====
    def begin_transaction(self) -> None:
        """开启事务"""
        if self._transaction_conn is None:
            self._transaction_conn = sqlite3.connect(self.db_path)
            self._transaction_conn.row_factory = sqlite3.Row
            self._transaction_conn.isolation_level = None  # 手动控制事务
            self._transaction_conn.execute('BEGIN')
    
    def commit_transaction(self) -> None:
        """提交事务"""
        if self._transaction_conn is not None:
            self._transaction_conn.commit()
            self._transaction_conn.close()
            self._transaction_conn = None
    
    def rollback_transaction(self) -> None:
        """回滚事务"""
        if self._transaction_conn is not None:
            self._transaction_conn.rollback()
            self._transaction_conn.close()
            self._transaction_conn = None
    
    def get_intent_by_id(self, intent_id: int) -> Optional[Dict[str, Any]]:
        """根据ID查询意图"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT intent_id, intent_code, intent_name, parent_id, level, priority, is_enabled, description
                FROM intents 
                WHERE intent_id = ?
            ''', (intent_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_all_intents(self) -> List[Dict[str, Any]]:
        """查询所有意图"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT intent_id, intent_code, intent_name, parent_id, level, priority, is_enabled, description
                FROM intents 
                ORDER BY level, priority DESC
            ''')
            return [dict(row) for row in cursor.fetchall()]
    
    def get_keyword_by_text_and_relation(self, keyword: str, type: str, relation_id: int) -> Optional[Dict[str, Any]]:
        """根据关键词文本和关联ID查询关键词"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT keyword_id, keyword, type, relation_id, weight, is_enabled, description
                FROM keywords 
                WHERE keyword = ? AND type = ? AND relation_id = ?
            ''', (keyword, type, relation_id))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def add_keyword(self, keyword: str, type: str, relation_id: int, weight: float, is_enabled: int, description: str = "") -> int:
        """新增关键词"""
        with self.get_connection(write=True) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO keywords (keyword, type, relation_id, weight, is_enabled, description)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (keyword, type, relation_id, weight, is_enabled, description))
            conn.commit()
            return cursor.lastrowid
    
    def update_keyword_weight(self, keyword_id: int, weight: float) -> bool:
        """更新关键词权重"""
        with self.get_connection(write=True) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE keywords 
                SET weight = ? 
                WHERE keyword_id = ?
            ''', (weight, keyword_id))
            conn.commit()
            return cursor.rowcount > 0
    
    def get_entity_by_type(self, entity_type: str) -> Optional[Dict[str, Any]]:
        """根据实体类型查询实体信息"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT entity_id, entity_code, entity_name, entity_type, description
                FROM entities 
                WHERE entity_type = ?
            ''', (entity_type,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def save_route_record(self, intent: Dict[str, Any], entities: List[Dict[str, Any]]) -> int:
        """保存路由记录"""
        with self.get_connection(write=True) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO route_records (intent_id, intent_name, entities, create_time)
                VALUES (?, ?, ?, datetime('now'))
            ''', (
                intent.get("intent_id", 0),
                intent.get("intent_name", ""),
                str(entities)
            ))
            conn.commit()
            return cursor.lastrowid
    
    def get_all_entities(self) -> List[Dict[str, Any]]:
        """查询所有实体"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT entity_id, entity_code, entity_name, entity_type, description
                FROM entities 
                ORDER BY entity_name
            ''')
            return [dict(row) for row in cursor.fetchall()]
    
    def get_all_keywords(self, type: Optional[str] = None, relation_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """查询关键词列表"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            sql = '''
                SELECT keyword_id, keyword, type, relation_id, weight, is_enabled, description
                FROM keywords 
                WHERE 1=1
            '''
            params = []
            if type:
                sql += " AND type = ?"
                params.append(type)
            if relation_id:
                sql += " AND relation_id = ?"
                params.append(relation_id)
            sql += " ORDER BY weight DESC"
            cursor.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_business_entity_keyword_cache(self, industry_code: str = "default") -> Dict[str, Any]:
        """获取业务实体关键词缓存，用于快速匹配"""
        # 暂时简化实现，返回空字典，后续完善业务实体规则
        return {}
    
    def get_business_entity_cache(self, industry_code: str = "default") -> Dict[str, Any]:
        """获取业务实体缓存，用于实体提取匹配"""
        # 暂时简化实现，返回空字典，后续完善业务实体规则
        return {}
    
    # ===== 扩展接口，适配现有核心模块 =====
    def get_all_intent_neurons(self) -> List[Dict[str, Any]]:
        """获取所有意图神经元"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM intent_neurons')
            return [dict(row) for row in cursor.fetchall()]
    
    def get_synapse_weights_by_intent(self, intent_id: int) -> List[Dict[str, Any]]:
        """获取意图的突触权重"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM synapse_weights WHERE intent_id = ?', (intent_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_intent_keyword_cache(self) -> Dict[str, List[Dict[str, Any]]]:
        """获取意图关键词缓存"""
        # 简化实现，后续完善
        return {}
    
    def get_intent_dict_cache(self) -> Dict[str, Dict[str, Any]]:
        """获取意图字典缓存"""
        return {}
    
    def get_emotion_keyword_cache(self) -> Dict[str, float]:
        """获取情绪关键词缓存"""
        return {}
    
    def get_emotion_dict_cache(self) -> Dict[str, Dict[str, Any]]:
        """获取情绪字典缓存"""
        return {}
    
    def get_entity_keyword_cache(self) -> Dict[str, List[Dict[str, Any]]]:
        """获取实体关键词缓存"""
        return {}
    
    # ===== 管理后台API专用方法 =====
    def add_intent(self, intent_code: str, intent_name: str, parent_id: int, level: int, priority: int, is_enabled: int, description: str = "") -> int:
        """新增意图"""
        with self.get_connection(write=True) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO intents (intent_code, intent_name, parent_id, level, priority, is_enabled, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (intent_code, intent_name, parent_id, level, priority, is_enabled, description))
            conn.commit()
            return cursor.lastrowid
    
    def update_intent(self, intent_id: int, intent_code: str = None, intent_name: str = None, parent_id: int = None, level: int = None, priority: int = None, is_enabled: int = None, description: str = None) -> bool:
        """更新意图（支持部分字段更新）"""
        with self.get_connection(write=True) as conn:
            cursor = conn.cursor()
            # 动态构建更新语句
            update_fields = []
            params = []
            
            if intent_code is not None:
                update_fields.append("intent_code = ?")
                params.append(intent_code)
            if intent_name is not None:
                update_fields.append("intent_name = ?")
                params.append(intent_name)
            if parent_id is not None:
                update_fields.append("parent_id = ?")
                params.append(parent_id)
            if level is not None:
                update_fields.append("level = ?")
                params.append(level)
            if priority is not None:
                update_fields.append("priority = ?")
                params.append(priority)
            if is_enabled is not None:
                update_fields.append("is_enabled = ?")
                params.append(is_enabled)
            if description is not None:
                update_fields.append("description = ?")
                params.append(description)
            
            if not update_fields:
                return False
            
            params.append(intent_id)
            sql = f"UPDATE intents SET {', '.join(update_fields)} WHERE intent_id = ?"
            cursor.execute(sql, params)
            conn.commit()
            return cursor.rowcount > 0
    
    def delete_intent(self, intent_id: int) -> bool:
        """删除意图（同步删除关联的关键词）"""
        with self.get_connection(write=True) as conn:
            cursor = conn.cursor()
            # 删除关联关键词
            cursor.execute('DELETE FROM keywords WHERE relation_id = ? AND type = "intent"', (intent_id,))
            # 删除意图
            cursor.execute('DELETE FROM intents WHERE intent_id = ?', (intent_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def update_keyword(self, keyword_id: int, keyword: str, weight: float, is_enabled: int, description: str = "") -> bool:
        """更新关键词"""
        with self.get_connection(write=True) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE keywords 
                SET keyword = ?, weight = ?, is_enabled = ?, description = ?
                WHERE keyword_id = ?
            ''', (keyword, weight, is_enabled, description, keyword_id))
            conn.commit()
            return cursor.rowcount > 0
    
    def delete_keyword(self, keyword_id: int) -> bool:
        """删除关键词"""
        with self.get_connection(write=True) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM keywords WHERE keyword_id = ?', (keyword_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def get_route_records(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """查询路由记录"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM route_records 
                ORDER BY create_time DESC 
                LIMIT ? OFFSET ?
            ''', (limit, offset))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_route_count(self) -> int:
        """获取路由记录总数"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) as count FROM route_records')
            row = cursor.fetchone()
            return row["count"] if row else 0
    
    def get_stats_by_time_range(self, start_time: str, end_time: str) -> Dict[str, Any]:
        """获取时间范围内的统计数据"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_requests,
                    COUNT(DISTINCT intent_id) as total_intents,
                    AVG(confidence) as avg_confidence
                FROM route_records 
                WHERE create_time BETWEEN ? AND ?
            ''', (start_time, end_time))
            row = cursor.fetchone()
            return dict(row) if row else {
                "total_requests": 0,
                "total_intents": 0,
                "avg_confidence": 0
            }
