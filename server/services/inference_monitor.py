"""
推理监控器
跟踪 LLM 推理性能指标：token生成数量、速度、请求统计等
"""

import time
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from collections import deque
from datetime import datetime


@dataclass
class RequestStats:
    """单个请求的统计信息"""
    request_id: str
    model_id: str
    start_time: float
    end_time: Optional[float] = None
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    tokens_per_second: float = 0.0
    status: str = "processing"  # processing, completed, failed
    error_message: Optional[str] = None


@dataclass
class ModelStats:
    """单个模型的统计信息"""
    model_id: str
    total_requests: int = 0
    completed_requests: int = 0
    failed_requests: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    avg_tokens_per_second: float = 0.0
    avg_response_time: float = 0.0
    current_requests: int = 0
    last_updated: float = field(default_factory=time.time)
    
    # 历史记录（保留最近100个请求）
    recent_requests: deque = field(default_factory=lambda: deque(maxlen=100))


class InferenceMonitor:
    """推理监控器 - 单例模式"""
    _instance = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._model_stats: Dict[str, ModelStats] = {}
        self._active_requests: Dict[str, RequestStats] = {}
        self._global_stats = {
            "total_requests": 0,
            "completed_requests": 0,
            "failed_requests": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_tokens": 0,
            "avg_tokens_per_second": 0.0,
            "avg_response_time": 0.0,
            "current_active_requests": 0,
            "start_time": time.time()
        }
        self._lock = asyncio.Lock()
        
        # 性能历史（用于计算实时速度）
        self._token_history: deque = deque(maxlen=60)  # 60秒历史
        self._request_history: deque = deque(maxlen=60)
    
    async def start_request(self, request_id: str, model_id: str, input_tokens: int = 0) -> None:
        """开始记录一个请求"""
        async with self._lock:
            stats = RequestStats(
                request_id=request_id,
                model_id=model_id,
                start_time=time.time(),
                input_tokens=input_tokens
            )
            self._active_requests[request_id] = stats
            
            # 更新模型统计
            if model_id not in self._model_stats:
                self._model_stats[model_id] = ModelStats(model_id=model_id)
            
            self._model_stats[model_id].total_requests += 1
            self._model_stats[model_id].current_requests += 1
            self._model_stats[model_id].last_updated = time.time()
            
            # 更新全局统计
            self._global_stats["total_requests"] += 1
            self._global_stats["current_active_requests"] += 1
    
    async def end_request(
        self, 
        request_id: str, 
        output_tokens: int, 
        status: str = "completed",
        error_message: Optional[str] = None
    ) -> None:
        """结束记录一个请求"""
        async with self._lock:
            if request_id not in self._active_requests:
                return
            
            request = self._active_requests[request_id]
            request.end_time = time.time()
            request.output_tokens = output_tokens
            request.total_tokens = request.input_tokens + output_tokens
            request.status = status
            request.error_message = error_message
            
            # 计算生成速度
            duration = request.end_time - request.start_time
            if duration > 0 and output_tokens > 0:
                request.tokens_per_second = output_tokens / duration
            
            # 更新模型统计
            model_id = request.model_id
            if model_id in self._model_stats:
                model_stats = self._model_stats[model_id]
                model_stats.current_requests -= 1
                model_stats.last_updated = time.time()
                
                if status == "completed":
                    model_stats.completed_requests += 1
                    model_stats.total_input_tokens += request.input_tokens
                    model_stats.total_output_tokens += output_tokens
                    model_stats.total_tokens += request.total_tokens
                    
                    # 更新平均速度
                    n = model_stats.completed_requests
                    model_stats.avg_tokens_per_second = (
                        (model_stats.avg_tokens_per_second * (n - 1) + request.tokens_per_second) / n
                    )
                    model_stats.avg_response_time = (
                        (model_stats.avg_response_time * (n - 1) + duration) / n
                    )
                else:
                    model_stats.failed_requests += 1
                
                # 添加到历史记录
                model_stats.recent_requests.append({
                    "request_id": request_id,
                    "timestamp": request.end_time,
                    "input_tokens": request.input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": request.total_tokens,
                    "tokens_per_second": request.tokens_per_second,
                    "duration": duration,
                    "status": status
                })
            
            # 更新全局统计
            self._global_stats["current_active_requests"] -= 1
            
            if status == "completed":
                self._global_stats["completed_requests"] += 1
                self._global_stats["total_input_tokens"] += request.input_tokens
                self._global_stats["total_output_tokens"] += output_tokens
                self._global_stats["total_tokens"] += request.total_tokens
                
                # 更新全局平均速度
                n = self._global_stats["completed_requests"]
                self._global_stats["avg_tokens_per_second"] = (
                    (self._global_stats["avg_tokens_per_second"] * (n - 1) + request.tokens_per_second) / n
                )
                self._global_stats["avg_response_time"] = (
                    (self._global_stats["avg_response_time"] * (n - 1) + duration) / n
                )
                
                # 添加到历史记录用于实时速度计算
                current_time = time.time()
                self._token_history.append((current_time, output_tokens))
                self._request_history.append((current_time, 1))
            else:
                self._global_stats["failed_requests"] += 1
            
            # 从活跃请求中移除
            del self._active_requests[request_id]
    
    def get_current_speed(self, window_seconds: int = 10) -> float:
        """获取当前token生成速度（最近N秒）"""
        current_time = time.time()
        cutoff_time = current_time - window_seconds
        
        total_tokens = sum(
            tokens for t, tokens in self._token_history 
            if t >= cutoff_time
        )
        
        return total_tokens / window_seconds if window_seconds > 0 else 0.0
    
    def get_current_rps(self, window_seconds: int = 60) -> float:
        """获取当前请求速率（最近N秒）"""
        current_time = time.time()
        cutoff_time = current_time - window_seconds
        
        total_requests = sum(
            count for t, count in self._request_history 
            if t >= cutoff_time
        )
        
        return total_requests / window_seconds if window_seconds > 0 else 0.0
    
    async def get_global_stats(self) -> Dict[str, Any]:
        """获取全局统计信息"""
        async with self._lock:
            uptime = time.time() - self._global_stats["start_time"]
            return {
                "uptime_seconds": uptime,
                "total_requests": self._global_stats["total_requests"],
                "completed_requests": self._global_stats["completed_requests"],
                "failed_requests": self._global_stats["failed_requests"],
                "current_active_requests": self._global_stats["current_active_requests"],
                "total_input_tokens": self._global_stats["total_input_tokens"],
                "total_output_tokens": self._global_stats["total_output_tokens"],
                "total_tokens": self._global_stats["total_tokens"],
                "avg_tokens_per_second": round(self._global_stats["avg_tokens_per_second"], 2),
                "avg_response_time": round(self._global_stats["avg_response_time"], 2),
                "current_speed_tokens_per_sec": round(self.get_current_speed(10), 2),
                "current_rps": round(self.get_current_rps(60), 2)
            }
    
    async def get_model_stats(self, model_id: Optional[str] = None) -> Dict[str, Any]:
        """获取模型统计信息"""
        async with self._lock:
            if model_id:
                if model_id not in self._model_stats:
                    return {}
                stats = self._model_stats[model_id]
                return {
                    "model_id": stats.model_id,
                    "total_requests": stats.total_requests,
                    "completed_requests": stats.completed_requests,
                    "failed_requests": stats.failed_requests,
                    "current_requests": stats.current_requests,
                    "total_input_tokens": stats.total_input_tokens,
                    "total_output_tokens": stats.total_output_tokens,
                    "total_tokens": stats.total_tokens,
                    "avg_tokens_per_second": round(stats.avg_tokens_per_second, 2),
                    "avg_response_time": round(stats.avg_response_time, 2),
                    "recent_requests": list(stats.recent_requests)
                }
            else:
                return {
                    model_id: {
                        "model_id": stats.model_id,
                        "total_requests": stats.total_requests,
                        "completed_requests": stats.completed_requests,
                        "failed_requests": stats.failed_requests,
                        "current_requests": stats.current_requests,
                        "total_input_tokens": stats.total_input_tokens,
                        "total_output_tokens": stats.total_output_tokens,
                        "total_tokens": stats.total_tokens,
                        "avg_tokens_per_second": round(stats.avg_tokens_per_second, 2),
                        "avg_response_time": round(stats.avg_response_time, 2)
                    }
                    for model_id, stats in self._model_stats.items()
                }
    
    async def get_active_requests(self) -> List[Dict[str, Any]]:
        """获取当前活跃请求"""
        async with self._lock:
            current_time = time.time()
            return [
                {
                    "request_id": req.request_id,
                    "model_id": req.model_id,
                    "duration": round(current_time - req.start_time, 2),
                    "input_tokens": req.input_tokens,
                    "status": req.status
                }
                for req in self._active_requests.values()
            ]
    
    async def reset_stats(self) -> None:
        """重置所有统计"""
        async with self._lock:
            self._model_stats.clear()
            self._active_requests.clear()
            self._global_stats = {
                "total_requests": 0,
                "completed_requests": 0,
                "failed_requests": 0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_tokens": 0,
                "avg_tokens_per_second": 0.0,
                "avg_response_time": 0.0,
                "current_active_requests": 0,
                "start_time": time.time()
            }
            self._token_history.clear()
            self._request_history.clear()


# 全局监控器实例
_inference_monitor = None


def get_inference_monitor() -> InferenceMonitor:
    """获取推理监控器实例"""
    global _inference_monitor
    if _inference_monitor is None:
        _inference_monitor = InferenceMonitor()
    return _inference_monitor
