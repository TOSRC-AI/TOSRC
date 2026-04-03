#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
管理员接口 - 规则包管理
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from src.utils.logger import get_logger
from src.api.dependencies import verify_admin_api_key
from src.bootstrap.context import get_rule_package_manager
import os
import json
from datetime import datetime

logger = get_logger()
router = APIRouter(prefix="/v1/admin/rule", tags=["管理员接口 - 规则包管理"])

class RulePackageUpdateRequest(BaseModel):
    """更新规则包请求体"""
    is_enabled: Optional[int] = None
    description: Optional[str] = ""

@router.get("/packages", summary="获取规则包列表")
async def get_rule_package_list(api_key_auth: bool = Depends(verify_admin_api_key)):
    """
    获取已加载的规则包列表
    """
    try:
        rpm = get_rule_package_manager()
        scenes = rpm.list_all_scenes()
        
        result = []
        for scene in scenes:
            cache_info = rpm.rule_cache.get(scene, {})
            rule_data = cache_info.get("data", {})
            
            result.append({
                "package_id": scene,
                "scene": scene,
                "scene_name": rule_data.get("scene_name", scene),
                "file_path": cache_info.get("file_path", ""),
                "entity_rule_count": len(rule_data.get("entity_rules", [])),
                "intent_rule_count": len(rule_data.get("intent_rules", [])),
                "emotion_rule_count": len(rule_data.get("emotion_rules", [])),
                "is_enabled": rule_data.get("is_enabled", True),
                "last_modify_time": cache_info.get("modify_time", 0),
                "description": rule_data.get("description", "")
            })
        
        return {
            "code": 0,
            "message": "success",
            "data": result
        }
        
    except Exception as e:
        logger.error(f"获取规则包列表失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")

@router.post("/packages/upload", summary="上传规则包")
async def upload_rule_package(file: UploadFile = File(...), api_key_auth: bool = Depends(verify_admin_api_key)):
    """
    上传JSON格式规则包文件
    """
    try:
        # 检查文件格式
        if not file.filename.endswith(".json"):
            raise HTTPException(status_code=400, detail="仅支持JSON格式规则包文件")
        
        # 读取文件内容
        content = await file.read()
        try:
            rule_data = json.loads(content.decode("utf-8"))
        except:
            raise HTTPException(status_code=400, detail="JSON格式解析失败")
        
        # 校验必填字段
        if "scene" not in rule_data or "scene_name" not in rule_data:
            raise HTTPException(status_code=400, detail="规则包缺少必填字段: scene、scene_name")
        
        scene = rule_data["scene"]
        save_path = f"./rules/{scene}_rules.json"
        
        # 保存文件
        os.makedirs("./rules", exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(rule_data, f, ensure_ascii=False, indent=2)
        
        # 加载规则包
        rpm = get_rule_package_manager()
        success = rpm._load_rule_package(scene, save_path)
        
        if not success:
            os.remove(save_path)
            raise HTTPException(status_code=500, detail="规则包加载失败，请检查格式是否正确")
        
        logger.info(f"上传规则包成功: {scene} -> {save_path}")
        return {
            "code": 0,
            "message": "上传成功",
            "data": {
                "scene": scene,
                "scene_name": rule_data["scene_name"],
                "file_path": save_path
            }
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"上传规则包失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")

@router.post("/packages/reload/{scene}", summary="重载规则包")
async def reload_rule_package(scene: str, api_key_auth: bool = Depends(verify_admin_api_key)):
    """
    重新加载指定场景的规则包（热更新）
    """
    try:
        rpm = get_rule_package_manager()
        
        if scene not in rpm.rule_cache:
            raise HTTPException(status_code=404, detail="规则包不存在")
        
        cache_info = rpm.rule_cache[scene]
        success = rpm._load_rule_package(scene, cache_info["file_path"])
        
        if not success:
            raise HTTPException(status_code=500, detail="规则包重载失败")
        
        logger.info(f"重载规则包成功: {scene}")
        return {
            "code": 0,
            "message": "重载成功"
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"重载规则包失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"重载失败: {str(e)}")

@router.post("/packages/reload/all", summary="重载所有规则包")
async def reload_all_rule_packages(api_key_auth: bool = Depends(verify_admin_api_key)):
    """
    重新加载所有规则包（全量热更新）
    """
    try:
        rpm = get_rule_package_manager()
        rpm.reload_all()
        
        logger.info("全量重载所有规则包成功")
        return {
            "code": 0,
            "message": "全量重载成功"
        }
        
    except Exception as e:
        logger.error(f"全量重载规则包失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"重载失败: {str(e)}")

@router.post("/packages/update/{scene}", summary="更新规则包状态")
async def update_rule_package(scene: str, request: RulePackageUpdateRequest, api_key_auth: bool = Depends(verify_admin_api_key)):
    """
    更新规则包启用状态、描述信息
    """
    try:
        rpm = get_rule_package_manager()
        
        if scene not in rpm.rule_cache:
            raise HTTPException(status_code=404, detail="规则包不存在")
        
        pkg = rpm.rule_cache[scene]
        
        # 更新启用状态
        if request.is_enabled is not None:
            pkg["data"]["is_enabled"] = bool(request.is_enabled)
            rpm.rule_cache[scene] = pkg
        
        # 更新描述（保存到文件）
        if request.description is not None:
            pkg["description"] = request.description
            # 更新文件
            if os.path.exists(pkg["file_path"]):
                with open(pkg["file_path"], "r", encoding="utf-8") as f:
                    file_data = json.load(f)
                file_data["description"] = request.description
                with open(pkg["file_path"], "w", encoding="utf-8") as f:
                    json.dump(file_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"更新规则包成功: {scene}")
        return {
            "code": 0,
            "message": "更新成功"
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"更新规则包失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")

@router.post("/packages/delete/{scene}", summary="删除规则包")
async def delete_rule_package(scene: str, api_key_auth: bool = Depends(verify_admin_api_key)):
    """
    删除指定规则包
    """
    try:
        rpm = get_rule_package_manager()
        
        if scene not in rpm.rule_cache:
            raise HTTPException(status_code=404, detail="规则包不存在")
        
        pkg = rpm.rule_cache[scene]
        
        # 卸载规则包
        if scene in rpm.rule_cache:
            del rpm.rule_cache[scene]
        
        # 删除文件
        if os.path.exists(pkg["file_path"]):
            os.remove(pkg["file_path"])
        
        logger.info(f"删除规则包成功: {scene}")
        return {
            "code": 0,
            "message": "删除成功"
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"删除规则包失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")