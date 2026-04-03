from typing import Dict, Any, Optional
from src.bionic.db import bionic_db
from ...common.utils.logger import get_logger

logger = get_logger()

class RouterDecisionEngine:
    def __init__(self):
        self.route_config = {}
        self.default_route = "通用大模型服务"
        # 加载数据库中的路由配置
        self._load_route_from_db()

    def _load_route_from_db(self) -> None:
        """从数据库加载路由配置，首次启动自动初始化默认路由"""
        try:
            db_routes = bionic_db.get_all_route_mappings()
            self.route_config.update(db_routes)
            logger.info(f"从数据库加载路由配置成功，共{len(db_routes)}条路由规则")
            
            # 如果数据库中路由不足，自动初始化默认路由
            if len(db_routes) < 5:
                default_routes = {
                    "租房查询": "房屋租赁服务大模型",
                    "房源报修": "物业服务大模型",
                    "天气查询": "天气服务大模型",
                    "缴费查询": "生活缴费服务大模型",
                    "投诉建议": "客户服务大模型"
                }
                initialized = 0
                for intent_id, route_target in default_routes.items():
                    if intent_id not in db_routes or db_routes[intent_id] == "":
                        if bionic_db.update_intent_route_target(intent_id, route_target):
                            initialized += 1
                if initialized > 0:
                    logger.info(f"自动初始化默认路由完成，新增{initialized}条路由规则")
                    # 重新加载
                    db_routes = bionic_db.get_all_route_mappings()
                    self.route_config.update(db_routes)
                    
        except Exception as e:
            logger.error(f"加载数据库路由配置失败: {str(e)}")

    def load_route_config(self, config: Dict[str, Any]) -> None:
        """加载静态路由配置（与数据库配置合并）"""
        static_routes = config.get("routes", {})
        self.default_route = config.get("default_route", "通用大模型服务")
        self.route_config.update(static_routes)
        logger.info(f"加载静态路由配置成功，共{len(static_routes)}条静态路由")
        logger.info(f"总路由规则数: {len(self.route_config)}")

    def reload_route_config(self) -> None:
        """重新加载路由配置（动态更新）"""
        self._load_route_from_db()
        logger.info("路由配置已重新加载")

    def decide_route(
        self, rule_match_result: Optional[Dict[str, Any]] = None, model_match_result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        final_result = {"route_to": self.default_route, "confidence": 0.0, "source": "default", "action": {}}

        if rule_match_result and rule_match_result["confidence"] >= 0.7:
            # 优先使用配置的意图路由映射（全局配置优先级最高）
            intent = rule_match_result.get("intent", "")
            if intent in self.route_config:
                route_to = self.route_config[intent]
                final_result.update(
                    {
                        "route_to": route_to,
                        "confidence": rule_match_result["confidence"],
                        "source": "rule_engine",
                        "action": {"route_to": route_to, "response_type": "structured"},
                    }
                )
            else:
                # 没有配置的话使用规则中的路由
                final_result.update(
                    {
                        "route_to": rule_match_result["action"]["route_to"],
                        "confidence": rule_match_result["confidence"],
                        "source": "rule_engine",
                        "action": rule_match_result["action"],
                    }
                )
            return final_result

        if model_match_result and model_match_result["confidence"] >= 0.6:
            # 优先使用配置的意图路由映射（全局配置优先级最高）
            intent = model_match_result.get("intent", "")
            if intent in self.route_config:
                route_to = self.route_config[intent]
                final_result.update(
                    {
                        "route_to": route_to,
                        "confidence": model_match_result["confidence"],
                        "source": "model_engine",
                        "action": {"route_to": route_to, "response_type": "structured"},
                    }
                )
            else:
                # 没有配置的话使用模型返回的路由
                final_result.update(
                    {
                        "route_to": model_match_result["action"]["route_to"],
                        "confidence": model_match_result["confidence"],
                        "source": "model_engine",
                        "action": model_match_result["action"],
                    }
                )
            return final_result

        return final_result
