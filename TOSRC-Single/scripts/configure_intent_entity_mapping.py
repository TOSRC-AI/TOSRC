#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
租房行业意图-实体关联规则自动配置工具
按照业务逻辑自动生成关联关系，导入到intent_entity_mapping表
"""
import sys
from pathlib import Path

# 添加上层目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))

from src.config.loader import get_global_config
from src.adapter.dal.sqlite_dal import SQLiteDAL
from src.utils.logger import get_logger

logger = get_logger()

class IntentEntityMappingConfigurator:
    """意图-实体关联配置器"""
    
    def __init__(self, industry_code: str = "rental"):
        self.industry_code = industry_code
        # 初始化数据库连接
        global_config = get_global_config()
        self.db = SQLiteDAL(global_config["database"]["sqlite_path"])
        
        # 定义意图与实体的关联规则
        self.mapping_rules = {
            # 1. 找房检索类
            "rent_search": ["location", "house_type", "price", "lease_term", "facility", "rent_type", "feature"],
            "rent_search_by_location": ["location"],
            "rent_search_by_house": ["house_type", "feature", "floor", "orientation"],
            "rent_search_by_rent_type": ["lease_term", "rent_type"],
            "rent_search_by_price": ["price", "payment"],
            "rent_search_by_facility": ["facility"],
            "rent_search_by_rule": ["restriction", "rule"],
            "rent_search_by_tag": ["house_tag"],
            
            # 2. 租房咨询类
            "rent_consult": ["location", "house_type", "price", "fee", "facility", "lease_term", "payment"],
            "rent_consult_house_info": ["house_type", "feature", "floor", "orientation", "area"],
            "rent_consult_rent_rule": ["lease_term", "rent_type", "restriction"],
            "rent_consult_payment": ["payment", "price", "fee"],
            "rent_consult_fee": ["fee"],
            "rent_consult_checkin": ["time", "lease_term"],
            "rent_consult_facility": ["facility"],
            "rent_consult_community": ["facility", "location"],
            
            # 3. 房源状态查询类
            "rent_status_check": ["location", "house_type"],
            "rent_check_available": ["location", "house_type"],
            "rent_check_booked": ["location", "house_type"],
            "rent_check_viewed": ["location", "house_type"],
            
            # 4. 预约看房类
            "rent_appointment": ["location", "house_type", "time", "person", "phone"],
            "rent_appoint_view": ["location", "house_type", "time"],
            "rent_appoint_modify": ["time"],
            "rent_appoint_cancel": [],
            "rent_appoint_confirm": ["time", "location", "person", "phone"],
            
            # 5. 价格咨询/议价类
            "rent_price_ask": ["price", "house_type", "location", "lease_term"],
            "rent_ask_price": ["price", "location", "house_type"],
            "rent_ask_discount": ["price"],
            "rent_ask_bargain": ["price"],
            "rent_ask_price_include": ["fee", "price"],
            
            # 6. 租房申请/预订类
            "rent_apply": ["location", "house_type", "time", "person", "phone", "id_card"],
            "rent_apply_reserve": ["location", "house_type", "price", "time"],
            "rent_apply_sign": ["time", "person", "id_card"],
            "rent_apply_material": ["person", "id_card", "certificate"],
            "rent_apply_guarantee": ["person", "guarantee"],
            
            # 7. 租后服务类
            "rent_after_service": ["location", "house_type", "facility", "time", "person", "phone"],
            "rent_after_repair": ["facility", "time"],
            "rent_after_maintain": ["facility", "time"],
            "rent_after_complaint": ["person", "feature", "time"],
            "rent_after_consult": ["fee", "payment", "lease_term"],
            "rent_after_change": ["facility", "house_type"],
            
            # 8. 续租类
            "rent_renew": ["lease_term", "price", "payment", "time"],
            "rent_renew_apply": ["lease_term", "time"],
            "rent_renew_price": ["price", "lease_term"],
            "rent_renew_term": ["lease_term"],
            "rent_renew_contract": ["time"],
            
            # 9. 退租/解约类
            "rent_terminate": ["time", "lease_term", "fee", "price"],
            "rent_terminate_normal": ["time", "lease_term"],
            "rent_terminate_early": ["time", "lease_term", "fee"],
            "rent_terminate_deposit": ["fee", "price"],
            "rent_terminate_checkout": ["time"],
            
            # 10. 转租/换租类
            "rent_transfer": ["location", "house_type", "lease_term", "price", "person"],
            "rent_transfer_apply": ["house_type", "location", "time"],
            "rent_transfer_consult": ["lease_term", "fee"],
            "rent_change_house": ["location", "house_type", "price"],
            
            # 11. 其他辅助类
            "other_assist": ["person", "phone", "location"],
            "other_ask_agent": ["person", "phone"],
            "other_ask_policy": ["certificate", "fee"],
            "other_chat": []
        }
        
        # 必填实体配置（1=必填，0=可选）
        self.required_rules = {
            "rent_search_by_location": {"location": 1},
            "rent_search_by_price": {"price": 1},
            "rent_appoint_view": {"time": 1, "location": 1},
            "rent_ask_price": {"location": 1, "house_type": 1},
            "rent_after_repair": {"facility": 1},
            "rent_terminate_deposit": {"fee": 1}
        }
    
    def configure(self) -> bool:
        """配置所有关联规则"""
        try:
            logger.info("开始配置意图-实体关联规则...")
            
            # 开启事务
            self.db.begin_transaction()
            
            # 获取所有已存在的意图编码
            intent_codes = self._get_all_intent_codes()
            # 获取所有已存在的实体类型编码
            entity_codes = self._get_all_entity_codes()
            
            total_count = 0
            for intent_short_code, entity_types in self.mapping_rules.items():
                # 加上行业前缀
                intent_full_code = f"{self.industry_code}_{intent_short_code}"
                if intent_full_code not in intent_codes:
                    logger.debug(f"意图不存在，跳过: {intent_full_code}")
                    continue
                
                # 获取该意图的必填配置
                required_config = self.required_rules.get(intent_short_code, {})
                
                for entity_short_type in entity_types:
                    # 加上行业前缀
                    entity_full_code = f"{self.industry_code}_{entity_short_type}"
                    if entity_full_code not in entity_codes:
                        logger.debug(f"实体类型不存在，跳过: {entity_full_code}")
                        continue
                    
                    # 检查是否是必填
                    is_required = required_config.get(entity_short_type, 0)
                    
                    # 插入关联
                    success = self._insert_mapping(intent_full_code, entity_full_code, is_required)
                    if success:
                        total_count += 1
            
            self.db.commit_transaction()
            logger.info(f"✅ 意图-实体关联配置完成，共配置{total_count}条关联规则")
            return True
            
        except Exception as e:
            self.db.rollback_transaction()
            logger.error(f"配置失败，事务回滚: {str(e)}", exc_info=True)
            return False
    
    def _get_all_intent_codes(self) -> set:
        """获取所有已存在的意图编码"""
        try:
            result = self.db.execute_query("SELECT intent_code FROM intents WHERE industry_code = ?", (self.industry_code,))
            return set([item["intent_code"] for item in result])
        except Exception as e:
            logger.error(f"查询意图编码失败: {str(e)}")
            return set()
    
    def _get_all_entity_codes(self) -> set:
        """获取所有已存在的实体类型编码"""
        try:
            result = self.db.execute_query("SELECT entity_code FROM entity_types WHERE industry_code = ?", (self.industry_code,))
            return set([item["entity_code"] for item in result])
        except Exception as e:
            logger.error(f"查询实体类型编码失败: {str(e)}")
            return set()
    
    def _insert_mapping(self, intent_code: str, entity_code: str, is_required: int = 0) -> bool:
        """插入关联关系，存在则更新"""
        try:
            exists = self.db.execute_query(
                "SELECT id FROM intent_entity_mapping WHERE intent_code = ? AND entity_code = ?",
                (intent_code, entity_code)
            )
            
            if not exists:
                sql = """
                INSERT INTO intent_entity_mapping (intent_code, entity_code, is_required, priority)
                VALUES (?, ?, ?, 10)
                """
                params = (intent_code, entity_code, is_required)
                self.db.execute_update(sql, params)
                logger.debug(f"配置关联: {intent_code} -> {entity_code}，必填: {is_required}")
            return True
            
        except Exception as e:
            logger.debug(f"插入关联失败: {intent_code}->{entity_code}, 错误: {str(e)}")
            return False

def main():
    configurator = IntentEntityMappingConfigurator(industry_code="rental")
    configurator.configure()

if __name__ == "__main__":
    main()