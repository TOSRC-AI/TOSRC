"""
TOSRC 系统初始化引导模块
核心：通用底座初始化逻辑，单/多租户通用，无外网依赖
"""
import json
import os
from typing import List, Dict, Any
from ..utils.logger import get_logger
from ..interface.dal import BaseDAL

logger = get_logger()

class CoreInitializer:
    """Core层通用初始化器，所有租户版本通用"""
    
    def __init__(self, dal: BaseDAL):
        self.dal = dal
        # 资源文件路径
        self.resources_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "../../resources"
        )
        self.default_intents_path = os.path.join(self.resources_dir, "default_intents.json")
        self.schema_path = os.path.join(self.resources_dir, "schema.sql")
    
    def load_default_intents(self, force_update: bool = False) -> bool:
        """
        加载内置默认通用意图库
        :param force_update: 是否强制更新覆盖已有意图
        :return: 加载是否成功
        """
        try:
            # 检查是否已经加载过默认意图
            existing_top_intents = self.dal.execute_query(
                "SELECT COUNT(*) as count FROM intents WHERE parent_id = 0 AND is_builtin = 1"
            )
            if existing_top_intents and existing_top_intents[0]['count'] > 0 and not force_update:
                logger.info("默认内置意图库已经存在，跳过加载")
                return True
            
            # 读取内置意图文件
            if not os.path.exists(self.default_intents_path):
                logger.error(f"默认意图库文件不存在: {self.default_intents_path}")
                return False
            
            with open(self.default_intents_path, 'r', encoding='utf-8') as f:
                intent_data = json.load(f)
            
            intents = intent_data.get('intents', [])
            if not intents:
                logger.warning("默认意图库为空，跳过加载")
                return True
            
            logger.info(f"开始加载内置默认意图库，共 {len(intents)} 个顶层意图")
            
            # 开启事务
            self.dal.begin_transaction()
            
            try:
                # 先加载顶层意图
                top_intent_map = {}
                for top_intent in intents:
                    # 检查是否已存在
                    existing = self.dal.execute_query(
                        "SELECT intent_code FROM intents WHERE intent_code = ? AND parent_id = 0",
                        (top_intent['intent_code'],)
                    )
                    
                    if existing and not force_update:
                        logger.debug(f"顶层意图 {top_intent['intent_code']} 已存在，跳过")
                        continue
                    
                    # 插入顶层意图（新表结构）
                    self.dal.execute_insert(
                        """
                        INSERT INTO intents 
                        (intent_code, intent_name, level, parent_id, priority, is_enabled, description, is_builtin, industry_code, tenant_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, 1, '', '')
                        """,
                        (
                            top_intent['intent_code'],
                            top_intent['intent_name'],
                            top_intent['level'],
                            0,
                            top_intent['priority'],
                            top_intent['is_enabled'],
                            top_intent['description']
                        )
                    )
                    # 获取插入的顶层意图自增ID
                    top_intent_id = self.dal.execute_query("SELECT last_insert_rowid() as id")[0]["id"]
                    top_intent_code = top_intent['intent_code']
                    logger.info(f"新增顶层意图: {top_intent['intent_name']}({top_intent['intent_code']})")
                    
                    # 加载二级子意图
                    children = top_intent.get('children', [])
                    for child in children:
                        # 检查子意图是否已存在
                        existing_child = self.dal.execute_query(
                            "SELECT intent_code FROM intents WHERE intent_code = ?",
                            (child['intent_code'],)
                        )
                        
                        if existing_child and not force_update:
                            logger.debug(f"二级意图 {child['intent_code']} 已存在，跳过")
                            continue
                            
                        # 插入二级意图（新表结构）
                        self.dal.execute_insert(
                            """
                            INSERT INTO intents 
                            (intent_code, intent_name, level, parent_id, priority, is_enabled, description, is_builtin, industry_code, tenant_id)
                            VALUES (?, ?, ?, ?, ?, ?, ?, 1, '', '')
                            """,
                            (
                                child['intent_code'],
                                child['intent_name'],
                                child['level'],
                                top_intent_id,
                                child['priority'],
                                child['is_enabled'],
                                child['description']
                            )
                        )
                        logger.info(f"新增二级意图: {child['intent_name']}({child['intent_code']}) 父级: {top_intent['intent_code']}")
                
                self.dal.commit_transaction()
                logger.info("内置默认意图库加载完成，所有通用意图已就绪")
                return True
                
            except Exception as e:
                self.dal.rollback_transaction()
                logger.error(f"加载默认意图库失败，事务回滚: {str(e)}", exc_info=True)
                return False
                
        except Exception as e:
            logger.error(f"加载默认意图库异常: {str(e)}", exc_info=True)
            return False
    
    def initialize_database_schema(self) -> bool:
        """
        初始化数据库表结构
        :return: 初始化是否成功
        """
        try:
            if not os.path.exists(self.schema_path):
                logger.error(f"数据库表结构文件不存在: {self.schema_path}")
                return False
            
            with open(self.schema_path, 'r', encoding='utf-8') as f:
                sql_script = f.read()
            
            # 分割SQL语句
            sql_statements = [s.strip() for s in sql_script.split(';') if s.strip()]
            
            self.dal.begin_transaction()
            
            try:
                for sql in sql_statements:
                    self.dal.execute_update(sql)
                
                self.dal.commit_transaction()
                logger.info("数据库表结构初始化完成")
                return True
            except Exception as e:
                self.dal.rollback_transaction()
                logger.error(f"数据库表结构初始化失败: {str(e)}", exc_info=True)
                return False
                
        except Exception as e:
            logger.error(f"数据库表结构初始化异常: {str(e)}", exc_info=True)
            return False
    
    def initialize_all(self, force: bool = False) -> bool:
        """
        执行所有初始化操作
        :param force: 是否强制重新初始化
        :return: 初始化是否成功
        """
        logger.info("开始执行TOSRC Core通用初始化")
        
        # 1. 初始化数据库表结构
        schema_success = self.initialize_database_schema()
        if not schema_success:
            logger.error("数据库表结构初始化失败，初始化终止")
            return False
        
        # 2. 加载默认意图库
        intent_success = self.load_default_intents(force)
        if not intent_success:
            logger.error("默认意图库加载失败，初始化终止")
            return False
        
        # 后续可以添加更多初始化逻辑：默认实体、默认规则包、默认系统配置等
        logger.info("TOSRC Core通用初始化完成")
        return True