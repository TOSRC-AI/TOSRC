#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM标注模块：作为高精度标注器，将用户输入拆解为标准结构化数据
完全兼容《外接LLM调教系统方案》中的标注规范，支持多LLM接入、格式强制校验、标注数据自动入库
"""
import json
import re
from typing import Dict, Any, Optional
from ...common.utils.logger import get_logger
from ...common.interface.net import BaseNetworkAdapter
from ...common.interface.dal import BaseDAL

logger = get_logger()

class LLMAnnotator:
    """LLM标注器核心类
    依赖网络适配器，所有联网操作通过NetAdapter实现
    """
    def __init__(self, 
                 config: Dict[str, Any], 
                 net_adapter: BaseNetworkAdapter,
                 dal: Optional[BaseDAL] = None):
        """
        初始化LLM标注器
        :param config: LLM配置字典，由适配层传入
        :param net_adapter: 网络适配实例，单租户离线模式下会禁用联网
        :param dal: 数据访问层实例，用于存储标注结果
        """
        self.config = config
        self.net_adapter = net_adapter
        self.dal = dal
        
        # 初始化LLM客户端（仅联网模式下可用）
        self.client = self._init_client() if net_adapter and not net_adapter.is_offline_mode() else None
        
        # 标注结果存储路径由适配层配置
        self.annotation_dir = self.config.get("annotation_dir", "data/annotations")
        
        # 固定标注Prompt（严格遵循方案要求，禁止修改格式）
        self.annotation_prompt = """
你是一个专业的文本标注工具，仅输出严格符合以下JSON格式的标注结果，不添加任何解释、闲聊、补充内容，字段不可缺失、不可修改格式，数值需准确。
标注要求：
1. context：明确文本的领域（如房产、教育）、具体场景（如户型咨询、价格投诉）、语气（正常/急切/抱怨/礼貌）；
2. intent：明确用户真实意图（如query_house_area、complain_service），置信度填1.0，准确判断是否是否定意图、是否是疑问；
3. entities：提取所有相关实体，标注准确的起始/结束索引、单位、类型（normal/range/approx），不遗漏、不错标；
4. emotion：准确判断情感倾向（positive/negative/neutral）、情感强度（0-1）、具体情感类型（satisfied/complaining/urgent/calm）。

JSON格式模板（严格遵循，不可修改字段名）：
```JSON
{
  "text": "",
  "context": {
    "domain": "",
    "scene": "",
    "tone": ""
  },
  "intent": {
    "name": "",
    "confidence": 1.0,
    "is_negated": false,
    "is_question": true
  },
  "entities": [
    {
      "entity": "",
      "value": "",
      "start": 0,
      "end": 0,
      "unit": "",
      "type": ""
    }
  ],
  "emotion": {
    "sentiment": "",
    "level": 0.0,
    "type": ""
  }
}
```

用户输入：{text}
标注结果：
"""
    
    def _load_config(self) -> Dict[str, Any]:
        """加载LLM配置，不存在则创建默认配置"""
        default_config = {
            "provider": os.getenv("LLM_PROVIDER", "deepseek"),  # 支持 openai/volcengine/deepseek/aliyun/tencent/custom
            "api_key": os.getenv("LLM_API_KEY", ""),
            "base_url": os.getenv("LLM_BASE_URL", "https://api.deepseek.com"),  # DeepSeek官方接口地址
            "model": os.getenv("LLM_MODEL", "deepseek-chat"),  # DeepSeek对话模型
            "temperature": 0.1,  # 标注场景用低温度，保证结果稳定
            "max_tokens": 1000,
            "annotation_enabled": os.getenv("LLM_ANNOTATION_ENABLED", "true").lower() == "true",
            "auto_save_annotation": True  # 自动保存标注结果到本地
        }
        
        # 配置文件不存在则创建默认配置
        if not os.path.exists(self.config_path):
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(default_config, f, ensure_ascii=False, indent=2)
            logger.info("已创建默认LLM配置文件: config/llm_config.json，请配置API Key后使用")
            return default_config
        
        # 加载现有配置
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            # 补全缺失的配置项
            for key, value in default_config.items():
                if key not in config:
                    config[key] = value
            # 环境变量优先级最高，覆盖配置文件值
            if os.getenv("LLM_PROVIDER"):
                config["provider"] = os.getenv("LLM_PROVIDER")
            if os.getenv("LLM_API_KEY"):
                config["api_key"] = os.getenv("LLM_API_KEY")
            if os.getenv("LLM_BASE_URL"):
                config["base_url"] = os.getenv("LLM_BASE_URL")
            if os.getenv("LLM_MODEL"):
                config["model"] = os.getenv("LLM_MODEL")
            if os.getenv("LLM_ANNOTATION_ENABLED") is not None:
                config["annotation_enabled"] = os.getenv("LLM_ANNOTATION_ENABLED").lower() == "true"
            logger.info("LLM配置加载成功")
            return config
        except Exception as e:
            logger.error(f"LLM配置加载失败，使用默认配置: {str(e)}")
            return default_config
    
    def _init_client(self) -> Optional[Any]:
        """初始化LLM客户端"""
        if not self.config.get("annotation_enabled", False) or not self.config.get("api_key"):
            logger.warning("LLM标注功能未启用或未配置API Key")
            return None
        
        try:
            # 火山引擎等兼容OpenAI接口的服务商都可以直接使用OpenAI客户端
            if self.config["provider"] in ["openai", "custom", "volcengine", "doubao", "deepseek"]:
                client = openai.OpenAI(
                    api_key=self.config["api_key"],
                    base_url=self.config["base_url"]
                )
                logger.info(f"LLM客户端初始化成功: {self.config['provider']}, 模型: {self.config['model']}")
                return client
            else:
                logger.error(f"暂不支持的LLM服务商: {self.config['provider']}")
                return None
        except Exception as e:
            logger.error(f"LLM客户端初始化失败: {str(e)}")
            return None
    
    def _extract_json_from_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """从LLM响应中提取JSON，处理各种格式问题"""
        # 先尝试直接解析
        try:
            return json.loads(response_text.strip())
        except:
            pass
        
        # 尝试提取```JSON和```之间的内容
        json_match = re.search(r'```(?:JSON|json)?\s*([\s\S]*?)\s*```', response_text)
        if json_match:
            try:
                return json.loads(json_match.group(1).strip())
            except:
                pass
        
        # 尝试匹配第一个完整的JSON对象
        brace_count = 0
        start_idx = -1
        for i, char in enumerate(response_text):
            if char == '{':
                brace_count += 1
                if start_idx == -1:
                    start_idx = i
            elif char == '}':
                brace_count -= 1
                if brace_count == 0 and start_idx != -1:
                    try:
                        return json.loads(response_text[start_idx:i+1].strip())
                    except:
                        break
        
        logger.error("无法从LLM响应中提取有效JSON")
        return None
    
    def _validate_annotation(self, annotation: Dict[str, Any], original_text: str) -> bool:
        """校验标注结果是否符合格式要求"""
        required_fields = ["text", "context", "intent", "entities", "emotion"]
        for field in required_fields:
            if field not in annotation:
                logger.error(f"标注结果缺少必填字段: {field}")
                return False
        
        # 校验context字段
        if not all(k in annotation["context"] for k in ["domain", "scene", "tone"]):
            logger.error("context字段格式不正确")
            return False
        
        # 校验intent字段
        if not all(k in annotation["intent"] for k in ["name", "confidence", "is_negated", "is_question"]):
            logger.error("intent字段格式不正确")
            return False
        
        # 校验emotion字段
        if not all(k in annotation["emotion"] for k in ["sentiment", "level", "type"]):
            logger.error("emotion字段格式不正确")
            return False
        
        # 校验text是否匹配
        if annotation.get("text", "") != original_text:
            annotation["text"] = original_text
        
        return True
    
    def _save_annotation(self, text: str, scene: str, annotation: Dict[str, Any]) -> None:
        """保存标注结果到本地文件，按场景分类"""
        if not self.config.get("auto_save_annotation", True):
            return
        
        try:
            scene_dir = os.path.join(self.annotation_dir, scene)
            os.makedirs(scene_dir, exist_ok=True)
            
            # 用时间戳作为文件名
            import time
            timestamp = int(time.time() * 1000)
            file_path = os.path.join(scene_dir, f"{timestamp}.json")
            
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(annotation, f, ensure_ascii=False, indent=2)
            logger.debug(f"标注结果已保存: {file_path}")
        except Exception as e:
            logger.error(f"标注结果保存失败: {str(e)}")
    
    def annotate(self, text: str, scene: str = "rental") -> Optional[Dict[str, Any]]:
        """
        标注文本，返回标准结构化结果
        Args:
            text: 用户输入文本
            scene: 行业场景编码
        Returns:
            标准标注结果，失败返回None
        """
        if not self.client or not self.config.get("annotation_enabled", False):
            logger.warning("LLM标注功能未启用")
            return None
        
        try:
            # 构造Prompt
            prompt = self.annotation_prompt.replace("{text}", text)
            
            # 调用LLM
            response = self.client.chat.completions.create(
                model=self.config["model"],
                messages=[
                    {"role": "system", "content": "你是一个专业的文本标注工具，仅输出JSON格式的标注结果，不添加任何其他内容。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.config.get("temperature", 0.1),
                max_tokens=self.config.get("max_tokens", 1000)
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # 提取并解析JSON
            annotation = self._extract_json_from_response(response_text)
            if not annotation:
                logger.error(f"LLM响应解析失败: {response_text[:100]}...")
                return None
            
            # 校验标注格式
            if not self._validate_annotation(annotation, text):
                return None
            
            # 保存标注结果
            self._save_annotation(text, scene, annotation)
            
            logger.info(f"文本标注成功: {text[:50]}...")
            return annotation
            
        except Exception as e:
            logger.error(f"LLM标注失败: {str(e)}")
            return None

# 全局单例
# 全局实例已移除，由适配层根据场景创建
