#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
管理员接口 - 批量测试
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from src.utils.logger import get_logger
from src.api.dependencies import verify_admin_api_key
from src.bootstrap.context import get_scheduler
import os
import csv
import json
import uuid
from datetime import datetime

logger = get_logger()
router = APIRouter(prefix="/v1/admin/batch", tags=["管理员接口 - 批量测试"])

# 批量测试任务缓存
batch_tasks: Dict[str, Dict[str, Any]] = {}

class BatchTestStartRequest(BaseModel):
    """启动批量测试请求体"""
    case_list: List[Dict[str, str]]
    auto_learn: bool = False

@router.post("/test/start", summary="启动批量测试")
async def start_batch_test(request: BatchTestStartRequest, api_key_auth: bool = Depends(verify_admin_api_key)):
    """
    启动批量测试任务
    """
    try:
        scheduler = get_scheduler()
        task_id = str(uuid.uuid4())
        
        # 创建测试任务
        batch_tasks[task_id] = {
            "task_id": task_id,
            "status": "running",
            "total": len(request.case_list),
            "processed": 0,
            "success": 0,
            "failed": 0,
            "accuracy": 0,
            "results": [],
            "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 异步执行测试（简单实现，后续可改为线程池）
        import threading
        def run_test():
            success_count = 0
            results = []
            
            for case in request.case_list:
                try:
                    text = case.get("text", "")
                    expected_intent = case.get("expected_intent", "")
                    
                    if not text:
                        continue
                    
                    # 调用调度引擎执行
                    result = scheduler.process(text)
                    actual_intent = result.get("intent", {}).get("intent_name", "")
                    confidence = result.get("intent", {}).get("confidence", 0)
                    
                    # 判断是否匹配
                    is_match = (actual_intent == expected_intent) if expected_intent else (confidence >= 0.8)
                    
                    if is_match:
                        success_count += 1
                    
                    results.append({
                        "text": text,
                        "expected_intent": expected_intent,
                        "actual_intent": actual_intent,
                        "confidence": confidence,
                        "is_match": is_match,
                        "entities": result.get("entities", []),
                        "cost_time": result.get("cost_time", 0)
                    })
                    
                except Exception as e:
                    logger.error(f"测试用例执行失败: {str(e)}")
                    results.append({
                        "text": text,
                        "expected_intent": expected_intent,
                        "actual_intent": "",
                        "confidence": 0,
                        "is_match": False,
                        "error": str(e),
                        "entities": [],
                        "cost_time": 0
                    })
                finally:
                    batch_tasks[task_id]["processed"] += 1
            
            # 更新任务状态
            batch_tasks[task_id]["status"] = "completed"
            batch_tasks[task_id]["success"] = success_count
            batch_tasks[task_id]["failed"] = len(request.case_list) - success_count
            batch_tasks[task_id]["accuracy"] = round(success_count / len(request.case_list) * 100, 2) if len(request.case_list) > 0 else 0
            batch_tasks[task_id]["results"] = results
            
            # 自动学习（如果开启）
            if request.auto_learn:
                # 后续实现自动学习逻辑
                pass
        
        threading.Thread(target=run_test, daemon=True).start()
        
        return {
            "code": 0,
            "message": "测试任务已启动",
            "data": {
                "task_id": task_id,
                "total": len(request.case_list)
            }
        }
        
    except Exception as e:
        logger.error(f"启动批量测试失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"启动失败: {str(e)}")

@router.get("/test/status/{task_id}", summary="获取批量测试状态")
async def get_batch_test_status(task_id: str, api_key_auth: bool = Depends(verify_admin_api_key)):
    """
    获取批量测试任务状态和结果
    """
    try:
        if task_id not in batch_tasks:
            raise HTTPException(status_code=404, detail="测试任务不存在")
        
        task = batch_tasks[task_id]
        
        return {
            "code": 0,
            "message": "success",
            "data": {
                "task_id": task["task_id"],
                "status": task["status"],
                "total": task["total"],
                "processed": task["processed"],
                "success": task["success"],
                "failed": task["failed"],
                "accuracy": task["accuracy"],
                "create_time": task["create_time"]
            }
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"获取测试状态失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")

@router.get("/test/results/{task_id}", summary="获取批量测试详细结果")
async def get_batch_test_results(task_id: str, page: int = 1, page_size: int = 20, only_failed: bool = False, api_key_auth: bool = Depends(verify_admin_api_key)):
    """
    分页获取批量测试详细结果
    :param task_id: 测试任务ID
    :param page: 页码
    :param page_size: 每页数量
    :param only_failed: 是否只返回错误用例
    """
    try:
        if task_id not in batch_tasks:
            raise HTTPException(status_code=404, detail="测试任务不存在")
        
        task = batch_tasks[task_id]
        results = task["results"]
        
        # 过滤错误用例
        if only_failed:
            results = [r for r in results if not r["is_match"]]
        
        # 分页
        total = len(results)
        offset = (page - 1) * page_size
        paginated_results = results[offset:offset+page_size]
        
        return {
            "code": 0,
            "message": "success",
            "data": {
                "list": paginated_results,
                "total": total,
                "page": page,
                "page_size": page_size
            }
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"获取测试结果失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")

@router.post("/test/upload", summary="上传测试用例文件")
async def upload_test_cases(file: UploadFile = File(...), api_key_auth: bool = Depends(verify_admin_api_key)):
    """
    上传测试用例文件（支持CSV格式，必须包含text列，可选expected_intent列）
    """
    try:
        # 检查文件格式
        if not file.filename.endswith(".csv"):
            raise HTTPException(status_code=400, detail="仅支持CSV格式文件")
        
        # 保存临时文件
        os.makedirs("./temp", exist_ok=True)
        temp_path = f"./temp/{uuid.uuid4()}_{file.filename}"
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # 解析CSV文件
        try:
            case_list = []
            with open(temp_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                
                # 检查必填列
                if "text" not in reader.fieldnames:
                    raise HTTPException(status_code=400, detail="文件必须包含text列")
                
                # 读取行数据
                for row in reader:
                    text = str(row["text"]).strip()
                    if not text:
                        continue
                    
                    case = {"text": text}
                    if "expected_intent" in reader.fieldnames:
                        case["expected_intent"] = str(row["expected_intent"]).strip()
                    
                    case_list.append(case)
            
            # 删除临时文件
            os.remove(temp_path)
            
            return {
                "code": 0,
                "message": "解析成功",
                "data": {
                    "case_count": len(case_list),
                    "case_list": case_list[:100]  # 最多返回前100条预览
                }
            }
            
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise HTTPException(status_code=400, detail=f"文件解析失败: {str(e)}")
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"上传测试用例失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")

@router.get("/test/template/download", summary="下载测试用例模板")
async def download_test_template(api_key_auth: bool = Depends(verify_admin_api_key)):
    """
    下载测试用例CSV模板
    """
    from fastapi.responses import FileResponse
    import csv
    
    # 生成模板文件
    os.makedirs("./temp", exist_ok=True)
    template_path = "./temp/test_case_template.csv"
    
    with open(template_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["text", "expected_intent"])
        writer.writerow(["我要租两室一厅", "request_action"])
        writer.writerow(["明天天气怎么样", "question_query"])
        writer.writerow(["这个房子租金3000元", "inform"])
    
    return FileResponse(
        template_path,
        media_type="text/csv",
        filename="批量测试用例模板.csv"
    )

@router.get("/test/report/download/{task_id}", summary="下载测试报告")
async def download_test_report(task_id: str, api_key_auth: bool = Depends(verify_admin_api_key)):
    """
    下载批量测试报告CSV
    """
    try:
        if task_id not in batch_tasks:
            raise HTTPException(status_code=404, detail="测试任务不存在")
        
        task = batch_tasks[task_id]
        if task["status"] != "completed":
            raise HTTPException(status_code=400, detail="测试任务未完成")
        
        # 生成报告文件
        os.makedirs("./temp", exist_ok=True)
        report_path = f"./temp/batch_test_report_{task_id}.csv"
        
        with open(report_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            # 表头
            writer.writerow(["文本", "预期意图", "实际意图", "置信度", "是否匹配", "耗时(ms)", "实体"])
            
            # 写入结果
            for result in task["results"]:
                entities_str = ",".join([f"{k}:{v}" for k, v in result.get("entities", {}).items()])
                writer.writerow([
                    result["text"],
                    result["expected_intent"],
                    result["actual_intent"],
                    result["confidence"],
                    "是" if result["is_match"] else "否",
                    result["cost_time"],
                    entities_str
                ])
        
        return FileResponse(
            report_path,
            media_type="text/csv",
            filename=f"批量测试报告_{task['create_time'].replace(':', '-')}.csv"
        )
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"下载测试报告失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"下载失败: {str(e)}")