"""
系统管理 API
提供系统状态监控、后端管理和参数调整功能
"""

import os
import psutil
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/admin", tags=["系统管理"])

# 导入推理监控器
from ...services.inference_monitor import get_inference_monitor

# 管理器实例（将在 main.py 中注入）
_model_manager = None
_backend_manager = None
_idle_monitor = None


def set_managers(model_manager, backend_manager, idle_monitor=None):
    """设置管理器实例"""
    global _model_manager, _backend_manager, _idle_monitor
    _model_manager = model_manager
    _backend_manager = backend_manager
    _idle_monitor = idle_monitor


def get_model_manager():
    return _model_manager


def get_backend_manager():
    return _backend_manager


def get_idle_monitor():
    return _idle_monitor


# ============== 数据模型 ==============

class SystemStats(BaseModel):
    timestamp: float
    cpu: Dict[str, Any]
    memory: Dict[str, Any]
    disk: Dict[str, Any]
    network: Dict[str, Any]


class BackendStatus(BaseModel):
    loaded_models: List[str]
    current_model: Optional[str]
    max_loaded_models: int
    idle_monitor_enabled: bool
    idle_timeout: int


class IdleMonitorStatus(BaseModel):
    port: int
    enabled: bool
    idle_timeout: int
    model_id: Optional[str]
    idle_time: float
    is_idle: bool
    monitoring: bool


class ModelControlRequest(BaseModel):
    action: str  # "load", "unload", "reload"
    model_id: Optional[str] = None


class ConfigUpdateRequest(BaseModel):
    max_loaded_models: Optional[int] = None
    idle_timeout: Optional[int] = None
    idle_monitor_enabled: Optional[bool] = None


# ============== API 端点 ==============

@router.get("/system/stats")
async def get_system_stats():
    """获取系统实时状态（CPU、内存）"""
    try:
        # CPU 信息 - 只调用一次，interval=None 使用上次缓存值
        cpu_percent = psutil.cpu_percent(interval=None)
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()
        cpu_per_cpu = psutil.cpu_percent(interval=None, percpu=True)
        
        # 内存信息
        memory = psutil.virtual_memory()
        
        # 进程信息（当前Python进程）
        process = psutil.Process()
        process_memory = process.memory_info()
        
        return {
            "timestamp": time.time(),
            "cpu": {
                "percent": cpu_percent,
                "count": cpu_count,
                "frequency": cpu_freq.current if cpu_freq else None,
                "per_cpu": cpu_per_cpu
            },
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "used": memory.used,
                "percent": memory.percent,
                "process_rss": process_memory.rss,
                "process_vms": process_memory.vms
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取系统状态失败: {str(e)}")


@router.get("/system/history")
async def get_system_history(minutes: int = 60):
    """获取系统历史数据（用于图表）"""
    # 这里可以从数据库或内存中获取历史数据
    # 目前返回空数组，后续可以实现数据持久化
    return {
        "cpu_history": [],
        "memory_history": [],
        "time_range": f"last {minutes} minutes"
    }


@router.get("/backend/status")
async def get_backend_status():
    """获取后端管理器状态"""
    backend_manager = get_backend_manager()
    if not backend_manager:
        raise HTTPException(status_code=500, detail="Backend manager not initialized")
    
    try:
        config = backend_manager.config
        idle_config = config.get("idle_monitor", {})
        
        return {
            "loaded_models": backend_manager.get_loaded_models(),
            "current_model": backend_manager._current_model,
            "max_loaded_models": config.get("model_loading", {}).get("max_loaded_models", 1),
            "idle_monitor_enabled": idle_config.get("enabled", True),
            "idle_timeout": idle_config.get("timeout", 60),
            "model_count": len(backend_manager._loaded_models)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取后端状态失败: {str(e)}")


@router.get("/backend/processes")
async def get_backend_processes():
    """获取后端进程列表（llama-server 等）"""
    processes = []
    try:
        # 只获取必要的属性，不获取 cpu_percent（需要时间间隔）
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'memory_info', 'create_time']):
            try:
                pinfo = proc.info
                cmdline = pinfo.get('cmdline')
                if cmdline and any('llama-server' in str(cmd) or 'sglang' in str(cmd) for cmd in cmdline):
                    processes.append({
                        "pid": pinfo['pid'],
                        "name": pinfo['name'],
                        "cmdline": ' '.join(cmdline) if cmdline else '',
                        "cpu_percent": 0,  # 不计算，太慢
                        "memory_mb": pinfo['memory_info'].rss / 1024 / 1024 if pinfo.get('memory_info') else 0,
                        "create_time": pinfo['create_time']
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied, TypeError):
                continue
        return {"processes": processes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取进程列表失败: {str(e)}")


@router.post("/backend/control")
async def control_backend(request: ModelControlRequest):
    """控制后端（加载/卸载/重启模型）"""
    backend_manager = get_backend_manager()
    model_manager = get_model_manager()
    
    if not backend_manager or not model_manager:
        raise HTTPException(status_code=500, detail="Managers not initialized")
    
    try:
        if request.action == "unload":
            if not request.model_id:
                # 卸载所有模型
                loaded_models = backend_manager.get_loaded_models()
                for model_id in loaded_models:
                    await backend_manager.unload_model(model_id)
                    model_manager.update_model_status(model_id, "unloaded")
                return {"success": True, "message": f"已卸载 {len(loaded_models)} 个模型"}
            else:
                # 卸载指定模型
                success = await backend_manager.unload_model(request.model_id)
                if success:
                    model_manager.update_model_status(request.model_id, "unloaded")
                return {"success": success, "model_id": request.model_id}
        
        elif request.action == "reload":
            if not request.model_id:
                raise HTTPException(status_code=400, detail="reload 操作需要指定 model_id")
            
            # 先卸载
            await backend_manager.unload_model(request.model_id)
            
            # 重新加载
            model = model_manager.get_model(request.model_id)
            if not model:
                raise HTTPException(status_code=404, detail=f"模型不存在: {request.model_id}")
            
            success = await backend_manager.load_model(
                request.model_id,
                model.path,
                model.to_config()
            )
            if success:
                model_manager.update_model_status(request.model_id, "loaded")
            return {"success": success, "model_id": request.model_id}
        
        else:
            raise HTTPException(status_code=400, detail=f"不支持的操作: {request.action}")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"操作失败: {str(e)}")


@router.get("/idle-monitor/status")
async def get_idle_monitor_status():
    """获取空闲监控状态"""
    idle_monitor = get_idle_monitor()
    if not idle_monitor:
        return {"enabled": False, "monitors": []}
    
    try:
        monitors = []
        for port, monitor in idle_monitor._monitors.items():
            status = monitor.get_status()
            monitors.append({
                "port": status["port"],
                "enabled": status["enabled"],
                "idle_timeout": status["idle_timeout"],
                "model_id": status["model_id"],
                "idle_time": round(status["idle_time"], 2),
                "is_idle": status["is_idle"],
                "monitoring": status["monitoring"]
            })
        
        return {
            "enabled": True,
            "monitors": monitors,
            "total_monitors": len(monitors)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取空闲监控状态失败: {str(e)}")


@router.post("/idle-monitor/config")
async def update_idle_monitor_config(port: int, enabled: Optional[bool] = None, timeout: Optional[int] = None):
    """更新空闲监控配置"""
    idle_monitor = get_idle_monitor()
    if not idle_monitor:
        raise HTTPException(status_code=500, detail="Idle monitor not initialized")
    
    try:
        if port not in idle_monitor._monitors:
            raise HTTPException(status_code=404, detail=f"端口 {port} 未注册")
        
        monitor = idle_monitor._monitors[port]
        
        if enabled is not None:
            monitor.enabled = enabled
            if enabled:
                await monitor.start_monitoring()
            else:
                await monitor.stop_monitoring()
        
        if timeout is not None:
            monitor.idle_timeout = timeout
        
        return {
            "success": True,
            "port": port,
            "enabled": monitor.enabled,
            "timeout": monitor.idle_timeout
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新配置失败: {str(e)}")


@router.post("/config/update")
async def update_system_config(request: ConfigUpdateRequest):
    """更新系统配置"""
    backend_manager = get_backend_manager()
    if not backend_manager:
        raise HTTPException(status_code=500, detail="Backend manager not initialized")
    
    try:
        config = backend_manager.config
        
        if request.max_loaded_models is not None:
            if "model_loading" not in config:
                config["model_loading"] = {}
            config["model_loading"]["max_loaded_models"] = request.max_loaded_models
        
        if request.idle_timeout is not None or request.idle_monitor_enabled is not None:
            if "idle_monitor" not in config:
                config["idle_monitor"] = {}
            
            if request.idle_timeout is not None:
                config["idle_monitor"]["timeout"] = request.idle_timeout
                backend_manager._default_idle_timeout = request.idle_timeout
            
            if request.idle_monitor_enabled is not None:
                config["idle_monitor"]["enabled"] = request.idle_monitor_enabled
                backend_manager._idle_monitor_enabled = request.idle_monitor_enabled
        
        return {
            "success": True,
            "config": config
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新配置失败: {str(e)}")


# ============== 推理监控 API ==============

@router.get("/inference/stats")
async def get_inference_stats():
    """获取推理全局统计信息"""
    try:
        monitor = get_inference_monitor()
        stats = await monitor.get_global_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取推理统计失败: {str(e)}")


@router.get("/inference/model-stats")
async def get_model_inference_stats(model_id: Optional[str] = None):
    """获取模型推理统计信息"""
    try:
        monitor = get_inference_monitor()
        stats = await monitor.get_model_stats(model_id)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取模型统计失败: {str(e)}")


@router.get("/inference/active-requests")
async def get_active_requests():
    """获取当前活跃的推理请求"""
    try:
        monitor = get_inference_monitor()
        requests = await monitor.get_active_requests()
        return {"active_requests": requests, "count": len(requests)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取活跃请求失败: {str(e)}")


@router.post("/inference/reset-stats")
async def reset_inference_stats():
    """重置推理统计信息"""
    try:
        monitor = get_inference_monitor()
        await monitor.reset_stats()
        return {"success": True, "message": "推理统计已重置"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重置统计失败: {str(e)}")


@router.get("/logs")
async def get_system_logs(limit: int = 100, level: Optional[str] = None):
    """获取系统日志"""
    from ...utils.logger import get_logs
    
    try:
        logs = get_logs(limit=limit, level=level)
        return {"logs": logs, "total": len(logs)}
    except Exception as e:
        # 如果日志系统未实现，返回空数组
        return {"logs": [], "total": 0, "note": "日志系统未启用"}


@router.post("/backend/scan-running")
async def scan_running_backends():
    """扫描并注册已运行的 llama-server 进程"""
    import psutil
    import os
    import re
    
    backend_manager = get_backend_manager()
    model_manager = get_model_manager()
    
    if not backend_manager or not model_manager:
        raise HTTPException(status_code=500, detail="Managers not initialized")
    
    try:
        registered_count = 0
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                pinfo = proc.info
                cmdline = pinfo.get('cmdline')
                if not cmdline:
                    continue
                    
                cmd_str = ' '.join(cmdline)
                if 'llama-server' not in cmd_str:
                    continue
                
                # 解析模型路径和端口
                model_path = None
                port = 38521
                
                # 解析 -m 参数
                m_index = None
                for i, arg in enumerate(cmdline):
                    if arg == '-m' and i + 1 < len(cmdline):
                        model_path = cmdline[i + 1]
                        m_index = i
                        break
                
                # 解析 --port 参数
                for i, arg in enumerate(cmdline):
                    if arg == '--port' and i + 1 < len(cmdline):
                        port = int(cmdline[i + 1])
                        break
                
                if not model_path:
                    continue
                
                # 在模型管理器中查找匹配的模型（支持绝对路径和相对路径）
                matched_model = None
                for model_id, model in model_manager.models.items():
                    # 检查绝对路径匹配
                    if os.path.abspath(model.path) == os.path.abspath(model_path):
                        matched_model = model
                        break
                    # 检查相对路径匹配（去掉 models/ 前缀）
                    model_path_rel = model_path
                    if model_path_rel.startswith('models\\') or model_path_rel.startswith('models/'):
                        model_path_rel = model_path_rel[7:]
                    if model.path.endswith(model_path_rel):
                        matched_model = model
                        break
                
                if not matched_model:
                    continue
                
                # 检查模型是否已经注册
                if matched_model.id in backend_manager.get_loaded_models():
                    continue
                
                # 创建后端实例并手动注册
                from ...backends.llama_backend import LlamaBackend
                
                backend_config = {
                    "server_path": f"runtimes/llama/bin/llama-server.exe"
                }
                
                backend = LlamaBackend(backend_config, port)
                
                # 手动设置已初始化状态
                backend._model_path = matched_model.path
                backend._model_config = {
                    "id": matched_model.id,
                    "name": matched_model.name,
                    "type": matched_model.type,
                    "category": matched_model.category,
                    "backend": matched_model.backend,
                    "max_context": matched_model.max_context,
                    "gpu_layers": getattr(matched_model, 'gpu_layers', 99),
                    "parallel": getattr(matched_model, 'parallel', 1),
                    "batch_size": getattr(matched_model, 'batch_size', 512)
                }
                backend._process = psutil.Process(pinfo['pid'])
                
                # 注册到 backend_manager
                async with backend_manager._lock:
                    backend_manager._loaded_models[matched_model.id] = backend
                    if not backend_manager._current_model:
                        backend_manager._current_model = matched_model.id
                
                # 更新模型状态
                model_manager.update_model_status(matched_model.id, "loaded")
                
                registered_count += 1
                print(f"[Scan] Registered running model: {matched_model.id} on port {port}")
                
            except Exception as e:
                print(f"[Scan] Error processing process {pinfo.get('pid', 'unknown')}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        return {
            "success": True,
            "registered_count": registered_count,
            "message": f"成功注册 {registered_count} 个已运行的模型"
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"扫描失败: {str(e)}")


@router.get("/dashboard")
async def get_dashboard_data():
    """获取仪表盘综合数据（一次性获取所有关键信息）"""
    backend_manager = get_backend_manager()
    model_manager = get_model_manager()
    idle_monitor = get_idle_monitor()
    
    if not backend_manager or not model_manager:
        raise HTTPException(status_code=500, detail="Managers not initialized")
    
    try:
        # 系统状态
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        # 后端状态
        loaded_models = backend_manager.get_loaded_models()
        
        # 空闲监控状态
        idle_status = []
        if idle_monitor:
            for port, monitor in idle_monitor._monitors.items():
                status = monitor.get_status()
                idle_status.append({
                    "port": status["port"],
                    "model_id": status["model_id"],
                    "idle_time": round(status["idle_time"], 2),
                    "is_idle": status["is_idle"]
                })
        
        return {
            "system": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_used_gb": round(memory.used / 1024**3, 2),
                "memory_total_gb": round(memory.total / 1024**3, 2)
            },
            "backend": {
                "loaded_models": loaded_models,
                "current_model": backend_manager._current_model,
                "model_count": len(loaded_models)
            },
            "models": {
                "total": len(model_manager.models),
                "loaded": len(loaded_models)
            },
            "idle_monitor": idle_status,
            "timestamp": time.time()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取仪表盘数据失败: {str(e)}")
