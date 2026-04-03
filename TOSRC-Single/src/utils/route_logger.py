#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
路由记录 JSONL 日志管理器
替代 SQLite route_records 表，解决高并发写入性能问题
"""
import glob
import json
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Iterator

from .jsonl_logger import JSONLLogger


class RouteLogger:
    """
    路由记录日志管理器

    功能：
    - 高性能路由记录写入（JSONL 格式）
    - 支持时间范围查询
    - 统计分析（意图分布、模式分布等）
    - 兼容原 SQLite 接口

    与 SQLite 对比优势：
    - 写入性能：0.1ms vs 2-5ms
    - Schema 灵活：无需 ALTER TABLE
    - 便于日志收集：Filebeat/Fluentd 可直接读取
    - 自动归档：支持压缩旧日志
    """

    def __init__(self, log_dir: str = "data/logs/routes"):
        """
        初始化路由记录器

        Args:
            log_dir: 日志文件存放目录
        """
        self.log_dir = Path(log_dir)
        self.logger = JSONLLogger(log_dir, "routes", rotate_daily=True, buffer_size=50)

    def save(self,
             text: str,
             intent: Optional[Dict[str, Any]] = None,
             entities: Optional[List[Dict]] = None,
             confidence: float = 0.0,
             mode: str = "rule",
             latency_ms: int = 0,
             user_id: str = "anonymous",
             scene: str = "default",
             emotion: Optional[Dict] = None,
             request_id: Optional[str] = None,
             metadata: Optional[Dict] = None) -> None:
        """
        保存路由记录

        Args:
            text: 用户输入文本
            intent: 意图识别结果
            entities: 实体提取结果
            confidence: 置信度
            mode: 处理模式 (rule/llm/hybrid)
            latency_ms: 处理耗时（毫秒）
            user_id: 用户标识
            scene: 场景标识
            emotion: 情绪分析结果
            request_id: 请求追踪ID
            metadata: 额外元数据
        """
        # 构建记录
        record = {
            # 基础信息
            "text": text,
            "request_id": request_id or self._generate_request_id(),
            "timestamp": datetime.now().isoformat(),

            # 用户和场景
            "user_id": user_id,
            "scene": scene,

            # 意图信息（兼容原 SQLite 表结构）
            "intent_id": intent.get("intent_id") if intent else None,
            "intent_code": intent.get("intent_code") if intent else None,
            "intent_name": intent.get("intent_name") if intent else None,
            "confidence": confidence,

            # 实体信息
            "entities": entities or [],

            # 情绪分析
            "emotion": emotion,

            # 性能指标
            "mode": mode,
            "latency_ms": latency_ms,

            # 扩展字段
            "metadata": metadata or {}
        }

        # 写入日志（非立即写入，使用缓冲）
        self.logger.write(record, immediate=False)

    def _generate_request_id(self) -> str:
        """生成请求ID"""
        import uuid
        return str(uuid.uuid4())[:8]

    def flush(self):
        """强制刷新缓冲区到磁盘"""
        self.logger.flush()

    def query(self,
              start_time: Optional[datetime] = None,
              end_time: Optional[datetime] = None,
              intent_code: Optional[str] = None,
              user_id: Optional[str] = None,
              scene: Optional[str] = None,
              min_confidence: Optional[float] = None,
              mode: Optional[str] = None,
              limit: int = 100) -> List[Dict[str, Any]]:
        """
        查询路由记录

        Args:
            start_time: 起始时间
            end_time: 结束时间
            intent_code: 意图代码过滤
            user_id: 用户ID过滤
            scene: 场景过滤
            min_confidence: 最小置信度
            mode: 处理模式过滤
            limit: 最大返回条数

        Returns:
            匹配的记录列表
        """
        records = []

        # 确定需要读取的文件范围
        files = self._get_files_in_range(start_time, end_time)

        for file_path in files:
            # 构建过滤函数
            def filter_func(record: Dict) -> bool:
                if intent_code and record.get("intent_code") != intent_code:
                    return False
                if user_id and record.get("user_id") != user_id:
                    return False
                if scene and record.get("scene") != scene:
                    return False
                if mode and record.get("mode") != mode:
                    return False
                if min_confidence is not None and record.get("confidence", 0) < min_confidence:
                    return False
                return True

            # 读取文件
            file_records = JSONLLogger.read_all(
                file_path,
                start_time=start_time,
                end_time=end_time,
                filter_func=filter_func,
                limit=limit - len(records) if limit else None
            )

            records.extend(file_records)

            if limit and len(records) >= limit:
                return records[:limit]

        return records

    def query_stream(self,
                     start_time: Optional[datetime] = None,
                     end_time: Optional[datetime] = None,
                     filter_func: Optional[callable] = None) -> Iterator[Dict[str, Any]]:
        """
        流式查询路由记录（适合大数据量）

        Args:
            start_time: 起始时间
            end_time: 结束时间
            filter_func: 自定义过滤函数

        Yields:
            单条记录
        """
        files = self._get_files_in_range(start_time, end_time)

        for file_path in files:
            yield from JSONLLogger.read(file_path, start_time, end_time, filter_func)

    def _get_files_in_range(self,
                            start_time: Optional[datetime],
                            end_time: Optional[datetime]) -> List[Path]:
        """获取时间范围内的日志文件列表"""
        all_files = sorted(self.log_dir.glob("routes_*.jsonl*"), reverse=True)

        if not start_time and not end_time:
            return all_files

        filtered_files = []
        for f in all_files:
            # 从文件名解析日期
            try:
                date_str = f.stem.split("_")[1]
                file_date = datetime.strptime(date_str, "%Y-%m-%d")

                # 过滤
                if start_time and file_date < start_time.replace(hour=0, minute=0, second=0):
                    continue
                if end_time and file_date > end_time.replace(hour=23, minute=59, second=59):
                    continue

                filtered_files.append(f)
            except (IndexError, ValueError):
                # 无法解析日期的文件也包含
                filtered_files.append(f)

        return filtered_files

    def get_stats(self, days: int = 7) -> Dict[str, Any]:
        """
        获取统计信息

        Args:
            days: 统计近N天的数据

        Returns:
            统计数据字典
        """
        cutoff = datetime.now() - timedelta(days=days)

        # 统计计数器
        total = 0
        intent_counts = defaultdict(int)
        mode_counts = defaultdict(int)
        scene_counts = defaultdict(int)
        confidence_sum = 0.0
        latency_sum = 0.0

        # 时间分布（按小时）
        hourly_distribution = defaultdict(int)

        files = self._get_files_in_range(cutoff, None)

        for file_path in files:
            for record in JSONLLogger.read(file_path):
                # 跳过过旧的数据
                ts = record.get("timestamp")
                if ts:
                    record_time = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                    if record_time < cutoff:
                        continue

                total += 1

                # 意图统计
                intent_code = record.get("intent_code") or "unknown"
                intent_counts[intent_code] += 1

                # 模式统计
                mode = record.get("mode") or "unknown"
                mode_counts[mode] += 1

                # 场景统计
                scene = record.get("scene") or "default"
                scene_counts[scene] += 1

                # 置信度平均
                confidence = record.get("confidence", 0)
                confidence_sum += confidence

                # 延迟平均
                latency = record.get("latency_ms", 0)
                latency_sum += latency

                # 时间分布
                if ts:
                    hour = datetime.fromisoformat(ts.replace('Z', '+00:00')).strftime("%H:00")
                    hourly_distribution[hour] += 1

        # 计算平均值
        avg_confidence = confidence_sum / total if total > 0 else 0
        avg_latency = latency_sum / total if total > 0 else 0

        # 获取Top意图
        top_intents = dict(sorted(intent_counts.items(), key=lambda x: -x[1])[:10])

        return {
            "period_days": days,
            "total_requests": total,
            "average_confidence": round(avg_confidence, 4),
            "average_latency_ms": round(avg_latency, 2),
            "top_intents": top_intents,
            "mode_distribution": dict(mode_counts),
            "scene_distribution": dict(scene_counts),
            "hourly_distribution": dict(sorted(hourly_distribution.items())),
            "coverage_start": cutoff.isoformat(),
            "coverage_end": datetime.now().isoformat()
        }

    def get_intent_accuracy(self, days: int = 7) -> Dict[str, Any]:
        """
        获取意图识别准确率统计

        Args:
            days: 统计近N天

        Returns:
            准确率统计
        """
        cutoff = datetime.now() - timedelta(days=days)

        high_confidence = 0
        medium_confidence = 0
        low_confidence = 0
        total = 0

        files = self._get_files_in_range(cutoff, None)

        for file_path in files:
            for record in JSONLLogger.read(file_path):
                ts = record.get("timestamp")
                if ts:
                    record_time = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                    if record_time < cutoff:
                        continue

                total += 1
                confidence = record.get("confidence", 0)

                if confidence >= 0.9:
                    high_confidence += 1
                elif confidence >= 0.7:
                    medium_confidence += 1
                else:
                    low_confidence += 1

        return {
            "period_days": days,
            "total": total,
            "high_confidence": {
                "count": high_confidence,
                "percentage": round(high_confidence / total * 100, 2) if total > 0 else 0
            },
            "medium_confidence": {
                "count": medium_confidence,
                "percentage": round(medium_confidence / total * 100, 2) if total > 0 else 0
            },
            "low_confidence": {
                "count": low_confidence,
                "percentage": round(low_confidence / total * 100, 2) if total > 0 else 0
            }
        }

    def export_to_json(self,
                       output_path: str,
                       start_time: Optional[datetime] = None,
                       end_time: Optional[datetime] = None,
                       filter_func: Optional[callable] = None) -> int:
        """
        导出记录为 JSON 文件（用于数据分析）

        Args:
            output_path: 输出文件路径
            start_time: 起始时间
            end_time: 结束时间
            filter_func: 过滤函数

        Returns:
            导出的记录数
        """
        count = 0

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("[\n")

            first = True
            for record in self.query_stream(start_time, end_time, filter_func):
                if not first:
                    f.write(",\n")
                first = False

                f.write("  " + json.dumps(record, ensure_ascii=False, default=str))
                count += 1

            f.write("\n]\n")

        return count

    def archive_old_logs(self, days: int = 7, compress: bool = True) -> Dict[str, Any]:
        """
        归档旧日志

        Args:
            days: 归档N天前的日志
            compress: 是否压缩

        Returns:
            归档结果统计
        """
        cutoff = datetime.now() - timedelta(days=days)
        archive_dir = self.log_dir / "archive"
        archive_dir.mkdir(exist_ok=True)

        archived = []
        errors = []

        # 查找旧日志
        for jsonl_file in self.log_dir.glob("routes_*.jsonl"):
            if jsonl_file.suffix == '.gz':
                continue

            try:
                date_str = jsonl_file.stem.split("_")[1]
                file_date = datetime.strptime(date_str, "%Y-%m-%d")

                if file_date < cutoff:
                    if compress:
                        # 压缩
                        archive_path = archive_dir / f"{jsonl_file.stem}.jsonl.gz"
                        result = JSONLLogger.compress(jsonl_file, archive_path, remove_source=True)
                        archived.append(result)
                    else:
                        # 仅移动
                        archive_path = archive_dir / jsonl_file.name
                        jsonl_file.rename(archive_path)
                        archived.append({
                            "source": str(jsonl_file),
                            "dest": str(archive_path)
                        })

            except Exception as e:
                errors.append({"file": str(jsonl_file), "error": str(e)})

        return {
            "archived_count": len(archived),
            "error_count": len(errors),
            "archived_files": archived,
            "errors": errors
        }

    def get_log_stats(self) -> Dict[str, Any]:
        """获取日志文件统计"""
        return self.logger.get_stats()

    def close(self):
        """关闭日志记录器"""
        self.logger.close()
