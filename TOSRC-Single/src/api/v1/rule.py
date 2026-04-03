"""
规则管理API模块，包含规则包的加载、审核、重载等接口
"""
from fastapi import APIRouter, Depends, File, UploadFile
from typing import Optional, List, Dict, Any
import os
import json
from src.api.dependencies import verify_admin_api_key
from src.bootstrap.context import get_rule_package_manager
from src.utils.logger import logger

# 规则管理API路由
rule_router = APIRouter(tags=["规则管理"], prefix="/api/v1/admin/rule", dependencies=[Depends(verify_admin_api_key)])

@rule_router.get("/packages")
async def get_rule_packages():
    """获取所有规则包列表"""
    try:
        rpm = get_rule_package_manager()
        packages = []
        for scene, cache_info in rpm.rule_cache.items():
            packages.append({
                "scene": scene,
                "scene_name": cache_info["data"].get("scene_name", scene),
                "entity_rule_count": len(cache_info["data"].get("entity_rules", [])),
                "intent_rule_count": len(cache_info["data"].get("intent_rules", [])),
                "emotion_rule_count": len(cache_info["data"].get("emotion_rules", [])),
                "negative_rule_count": len(cache_info["data"].get("negative_rules", [])),
                "last_modify_time": cache_info["modify_time"],
                "file_path": cache_info["file_path"]
            })
        
        return {
            "code": 0,
            "message": "success",
            "data": {
                "list": packages,
                "total": len(packages)
            }
        }
    except Exception as e:
        logger.error(f"获取规则包列表失败：{str(e)}", exc_info=True)
        return {
            "code": 500,
            "message": f"获取规则包列表失败：{str(e)}",
            "data": None
        }

@rule_router.get("/package/{scene}")
async def get_rule_package_detail(scene: str):
    """获取规则包详情"""
    try:
        rpm = get_rule_package_manager()
        rules = rpm.get_scene_rules(scene)
        if not rules:
            return {
                "code": 404,
                "message": "规则包不存在",
                "data": None
            }
        
        return {
            "code": 0,
            "message": "success",
            "data": rules
        }
    except Exception as e:
        logger.error(f"获取规则包详情失败：{str(e)}", exc_info=True)
        return {
            "code": 500,
            "message": f"获取规则包详情失败：{str(e)}",
            "data": None
        }

@rule_router.post("/reload/{scene}")
async def reload_rule_package(scene: str):
    """重载指定规则包"""
    try:
        rpm = get_rule_package_manager()
        if scene not in rpm.rule_cache:
            return {
                "code": 404,
                "message": "规则包不存在",
                "data": None
            }
        
        success = rpm._load_rule_package(scene, rpm.rule_cache[scene]["file_path"])
        if success:
            logger.info(f"规则包重载成功：{scene}")
            return {
                "code": 0,
                "message": "重载成功",
                "data": None
            }
        return {
            "code": 500,
            "message": "重载失败",
            "data": None
        }
    except Exception as e:
        logger.error(f"重载规则包失败：{str(e)}", exc_info=True)
        return {
            "code": 500,
            "message": f"重载规则包失败：{str(e)}",
            "data": None
        }

@rule_router.post("/upload")
async def upload_rule_package(file: UploadFile = File(...)):
    """上传规则包"""
    try:
        # 校验文件格式
        if not file.filename.endswith("_rules.json"):
            return {
                "code": 400,
                "message": "规则包文件名必须以_rules.json结尾",
                "data": None
            }
        
        # 读取文件内容
        content = await file.read()
        rule_data = json.loads(content.decode("utf-8"))
        
        # 校验格式
        required_fields = ["scene", "entity_rules", "intent_rules", "emotion_rules", "negative_rules"]
        for field in required_fields:
            if field not in rule_data:
                return {
                    "code": 400,
                    "message": f"规则包缺少必填字段：{field}",
                    "data": None
                }
        
        # 保存文件
        scene = rule_data["scene"]
        save_path = os.path.join("./rules", f"{scene}_rules.json")
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(rule_data, f, ensure_ascii=False, indent=2)
        
        # 加载规则包
        rpm = get_rule_package_manager()
        success = rpm._load_rule_package(scene, save_path)
        
        if success:
            logger.info(f"规则包上传成功：{scene}")
            return {
                "code": 0,
                "message": "上传成功",
                "data": {"scene": scene}
            }
        return {
            "code": 500,
            "message": "规则包加载失败",
            "data": None
        }
    except Exception as e:
        logger.error(f"上传规则包失败：{str(e)}", exc_info=True)
        return {
            "code": 500,
            "message": f"上传规则包失败：{str(e)}",
            "data": None
        }