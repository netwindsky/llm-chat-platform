"""
详细的日志系统
包含错误追踪、性能指标、系统状态监控
"""

import logging
import sys
import traceback
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from functools import wraps
import psutil
import os


class SystemLogger:
    """系统日志管理器"""

    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

        # 创建不同级别的日志文件
        self.app_log = self.log_dir / "app.log"
        self.error_log = self.log_dir / "error.log"
        self.performance_log = self.log_dir / "performance.log"
        self.system_log = self.log_dir / "system.log"

        # 配置日志格式
        self.formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)d] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # 详细格式（包含更多信息）
        self.detailed_formatter = logging.Formatter(
            '[%(asctime)s.%(msecs)03d] [%(levelname)s] [%(name)s:%(lineno)d] [%(funcName)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # 初始化日志记录器
        self._setup_loggers()

    def _setup_loggers(self):
        """设置日志记录器"""
        # 应用日志
        self.logger = logging.getLogger("llm_server")
        self.logger.setLevel(logging.DEBUG)

        # 文件处理器
        file_handler = logging.FileHandler(self.app_log, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(self.formatter)
        self.logger.addHandler(file_handler)

        # 错误日志（单独记录错误）
        error_handler = logging.FileHandler(self.error_log, encoding='utf-8')
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(self.detailed_formatter)
        self.logger.addHandler(error_handler)

        # 控制台输出
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(self.formatter)
        self.logger.addHandler(console_handler)

        # 性能日志记录器
        self.perf_logger = logging.getLogger("llm_server.performance")
        self.perf_logger.setLevel(logging.DEBUG)
        perf_handler = logging.FileHandler(self.performance_log, encoding='utf-8')
        perf_handler.setFormatter(self.detailed_formatter)
        self.perf_logger.addHandler(perf_handler)

        # 系统日志记录器
        self.sys_logger = logging.getLogger("llm_server.system")
        self.sys_logger.setLevel(logging.DEBUG)
        sys_handler = logging.FileHandler(self.system_log, encoding='utf-8')
        sys_handler.setFormatter(self.detailed_formatter)
        self.sys_logger.addHandler(sys_handler)

    def log_request(self, method: str, path: str, model: str, **kwargs):
        """记录请求信息"""
        data = {
            "timestamp": datetime.now().isoformat(),
            "type": "request",
            "method": method,
            "path": path,
            "model": model,
            **kwargs
        }
        self.logger.info(f"REQUEST | {json.dumps(data, ensure_ascii=False)}")

    def log_response(self, method: str, path: str, status_code: int, duration_ms: float, **kwargs):
        """记录响应信息"""
        data = {
            "timestamp": datetime.now().isoformat(),
            "type": "response",
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": round(duration_ms, 2),
            **kwargs
        }
        self.logger.info(f"RESPONSE | {json.dumps(data, ensure_ascii=False)}")

    def log_error(self, error: Exception, context: Dict[str, Any] = None, request_info: Dict[str, Any] = None):
        """详细记录错误信息"""
        error_data = {
            "timestamp": datetime.now().isoformat(),
            "type": "error",
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc(),
            "context": context or {},
            "request_info": request_info or {},
            "system_info": self._get_system_info()
        }

        # 记录到错误日志
        self.logger.error(f"ERROR | {json.dumps(error_data, ensure_ascii=False, indent=2)}")

        # 同时输出到控制台
        print(f"\n{'='*80}")
        print(f"ERROR: {type(error).__name__}: {error}")
        print(f"{'='*80}")
        print(traceback.format_exc())
        print(f"{'='*80}\n")

    def log_performance(self, operation: str, duration_ms: float, **metrics):
        """记录性能指标"""
        data = {
            "timestamp": datetime.now().isoformat(),
            "type": "performance",
            "operation": operation,
            "duration_ms": round(duration_ms, 2),
            **metrics
        }
        self.perf_logger.info(f"PERF | {json.dumps(data, ensure_ascii=False)}")

    def log_system_status(self):
        """记录系统状态"""
        status = {
            "timestamp": datetime.now().isoformat(),
            "type": "system_status",
            **self._get_system_info()
        }
        self.sys_logger.info(f"SYSTEM | {json.dumps(status, ensure_ascii=False)}")

    def log_model_event(self, event_type: str, model_id: str, **kwargs):
        """记录模型相关事件"""
        data = {
            "timestamp": datetime.now().isoformat(),
            "type": "model_event",
            "event": event_type,
            "model_id": model_id,
            **kwargs
        }
        self.logger.info(f"MODEL | {json.dumps(data, ensure_ascii=False)}")

    def log_llama_server_event(self, event_type: str, details: Dict[str, Any] = None):
        """记录 llama-server 相关事件"""
        data = {
            "timestamp": datetime.now().isoformat(),
            "type": "llama_server_event",
            "event": event_type,
            "details": details or {},
            "system_info": self._get_system_info()
        }
        self.sys_logger.info(f"LLAMA_SERVER | {json.dumps(data, ensure_ascii=False)}")

    def _get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        try:
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            info = {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "percent": memory.percent
                },
                "disk": {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "percent": round((disk.used / disk.total) * 100, 2)
                },
                "process": {
                    "pid": os.getpid(),
                    "memory_mb": round(psutil.Process().memory_info().rss / (1024**2), 2),
                    "threads": psutil.Process().num_threads()
                }
            }

            # 如果有 GPU，添加 GPU 信息
            try:
                import nvidia_ml_py3 as nvml
                nvml.nvmlInit()
                handle = nvml.nvmlDeviceGetHandleByIndex(0)
                gpu_info = nvml.nvmlDeviceGetMemoryInfo(handle)
                gpu_util = nvml.nvmlDeviceGetUtilizationRates(handle)
                info["gpu"] = {
                    "total_mb": round(gpu_info.total / (1024**2), 2),
                    "used_mb": round(gpu_info.used / (1024**2), 2),
                    "free_mb": round(gpu_info.free / (1024**2), 2),
                    "utilization": gpu_util.gpu
                }
            except:
                pass

            return info
        except Exception as e:
            return {"error": str(e)}

    def get_recent_errors(self, n: int = 10) -> list:
        """获取最近的错误日志"""
        try:
            with open(self.error_log, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                return lines[-n:] if len(lines) > n else lines
        except:
            return []

    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """获取性能摘要"""
        try:
            with open(self.performance_log, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            operations = {}
            for line in lines:
                try:
                    if "PERF |" in line:
                        data = json.loads(line.split("PERF |")[1])
                        op = data.get("operation")
                        duration = data.get("duration_ms")
                        if op and duration:
                            if op not in operations:
                                operations[op] = []
                            operations[op].append(duration)
                except:
                    continue

            summary = {}
            for op, durations in operations.items():
                summary[op] = {
                    "count": len(durations),
                    "avg_ms": round(sum(durations) / len(durations), 2),
                    "min_ms": round(min(durations), 2),
                    "max_ms": round(max(durations), 2)
                }

            return summary
        except Exception as e:
            return {"error": str(e)}


# 全局日志实例
system_logger = SystemLogger()


def log_execution_time(operation_name: str):
    """装饰器：记录函数执行时间"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = (time.time() - start) * 1000
                system_logger.log_performance(operation_name, duration, status="success")
                return result
            except Exception as e:
                duration = (time.time() - start) * 1000
                system_logger.log_performance(operation_name, duration, status="error", error=str(e))
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                duration = (time.time() - start) * 1000
                system_logger.log_performance(operation_name, duration, status="success")
                return result
            except Exception as e:
                duration = (time.time() - start) * 1000
                system_logger.log_performance(operation_name, duration, status="error", error=str(e))
                raise

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


# 导出便捷函数
def log_request(method: str, path: str, model: str, **kwargs):
    system_logger.log_request(method, path, model, **kwargs)


def log_response(method: str, path: str, status_code: int, duration_ms: float, **kwargs):
    system_logger.log_response(method, path, status_code, duration_ms, **kwargs)


def log_error(error: Exception, context: Dict[str, Any] = None, request_info: Dict[str, Any] = None):
    system_logger.log_error(error, context, request_info)


def log_performance(operation: str, duration_ms: float, **metrics):
    system_logger.log_performance(operation, duration_ms, **metrics)


def log_system_status():
    system_logger.log_system_status()


def log_model_event(event_type: str, model_id: str, **kwargs):
    system_logger.log_model_event(event_type, model_id, **kwargs)


def log_llama_server_event(event_type: str, details: Dict[str, Any] = None):
    system_logger.log_llama_server_event(event_type, details)
