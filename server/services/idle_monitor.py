#!/usr/bin/env python3
"""
Llama-Server 空闲监控管理器

功能：
- 监控每个 llama-server 实例的最后请求时间
- 当空闲时间超过设定阈值时，自动卸载模型
- 支持按端口区分不同的 llama-server 实例
- 可配置开关、空闲时间和目标端口
"""

import asyncio
import time
from typing import Dict, Any, Optional, Set
from datetime import datetime, timedelta
import httpx


class LlamaServerMonitor:
    """单个 llama-server 实例的监控器"""
    
    def __init__(self, port: int, idle_timeout: int = 60, enabled: bool = True):
        """
        初始化监控器
        
        Args:
            port: llama-server 端口
            idle_timeout: 空闲超时时间（秒），默认60秒
            enabled: 是否启用监控
        """
        self.port = port
        self.idle_timeout = idle_timeout
        self.enabled = enabled
        self.last_request_time = time.time()
        self.model_id: Optional[str] = None
        self._monitoring = False
        self._task: Optional[asyncio.Task] = None
        self._callback: Optional[callable] = None
        
    def update_last_request(self):
        """更新最后请求时间"""
        self.last_request_time = time.time()
        
    def set_model(self, model_id: str):
        """设置当前加载的模型"""
        self.model_id = model_id
        
    def set_callback(self, callback: callable):
        """设置卸载回调函数"""
        self._callback = callback
        
    async def start_monitoring(self):
        """开始监控"""
        if not self.enabled or self._monitoring:
            return
            
        self._monitoring = True
        self._task = asyncio.create_task(self._monitor_loop())
        print(f"[IdleMonitor] 开始监控端口 {self.port}，空闲超时: {self.idle_timeout}秒")
        
    async def stop_monitoring(self):
        """停止监控"""
        self._monitoring = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        print(f"[IdleMonitor] 停止监控端口 {self.port}")
        
    async def _monitor_loop(self):
        """监控循环"""
        while self._monitoring:
            try:
                await asyncio.sleep(10)  # 每10秒检查一次
                
                if not self.enabled or not self.model_id:
                    continue
                    
                idle_time = time.time() - self.last_request_time
                
                if idle_time >= self.idle_timeout:
                    print(f"[IdleMonitor] 端口 {self.port} 空闲 {idle_time:.1f}秒，超过阈值 {self.idle_timeout}秒")
                    
                    # 调用卸载回调
                    if self._callback:
                        try:
                            await self._callback(self.port, self.model_id)
                            self.model_id = None  # 清除模型ID
                        except Exception as e:
                            print(f"[IdleMonitor] 卸载模型失败: {e}")
                            
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[IdleMonitor] 监控循环错误: {e}")
                
    def get_status(self) -> Dict[str, Any]:
        """获取监控状态"""
        idle_time = time.time() - self.last_request_time if self.last_request_time else 0
        return {
            "port": self.port,
            "enabled": self.enabled,
            "idle_timeout": self.idle_timeout,
            "model_id": self.model_id,
            "last_request_time": self.last_request_time,
            "idle_time": idle_time,
            "is_idle": idle_time >= self.idle_timeout if self.enabled else False,
            "monitoring": self._monitoring
        }


class IdleMonitorManager:
    """空闲监控管理器 - 管理多个 llama-server 实例"""
    
    def __init__(self):
        self._monitors: Dict[int, LlamaServerMonitor] = {}
        self._backend_manager = None
        self._default_timeout = 60  # 默认60秒
        
    def set_backend_manager(self, backend_manager):
        """设置后端管理器"""
        self._backend_manager = backend_manager
        
    def register_server(self, port: int, idle_timeout: Optional[int] = None, enabled: bool = True) -> LlamaServerMonitor:
        """
        注册一个 llama-server 实例进行监控
        
        Args:
            port: llama-server 端口
            idle_timeout: 空闲超时时间（秒），None则使用默认值
            enabled: 是否启用监控
            
        Returns:
            LlamaServerMonitor 实例
        """
        if port in self._monitors:
            # 更新现有监控器配置
            monitor = self._monitors[port]
            monitor.enabled = enabled
            if idle_timeout is not None:
                monitor.idle_timeout = idle_timeout
            return monitor
            
        # 创建新监控器
        timeout = idle_timeout if idle_timeout is not None else self._default_timeout
        monitor = LlamaServerMonitor(port, timeout, enabled)
        monitor.set_callback(self._on_idle_timeout)
        self._monitors[port] = monitor
        
        if enabled:
            asyncio.create_task(monitor.start_monitoring())
            
        return monitor
        
    def unregister_server(self, port: int):
        """取消注册 llama-server 实例"""
        if port in self._monitors:
            monitor = self._monitors[port]
            asyncio.create_task(monitor.stop_monitoring())
            del self._monitors[port]
            
    def update_request_time(self, port: int):
        """更新指定端口的最后请求时间"""
        if port in self._monitors:
            self._monitors[port].update_last_request()
            
    def set_model_for_port(self, port: int, model_id: str):
        """为指定端口设置当前模型"""
        if port in self._monitors:
            self._monitors[port].set_model(model_id)
            
    def enable_monitoring(self, port: int, enabled: bool = True):
        """启用/禁用指定端口的监控"""
        if port in self._monitors:
            monitor = self._monitors[port]
            monitor.enabled = enabled
            
            if enabled and not monitor._monitoring:
                asyncio.create_task(monitor.start_monitoring())
            elif not enabled and monitor._monitoring:
                asyncio.create_task(monitor.stop_monitoring())
                
    def set_idle_timeout(self, port: int, timeout: int):
        """设置指定端口的空闲超时时间"""
        if port in self._monitors:
            self._monitors[port].idle_timeout = timeout
            
    async def _on_idle_timeout(self, port: int, model_id: str):
        """空闲超时回调 - 卸载模型"""
        print(f"[IdleMonitor] 端口 {port} 的模型 {model_id} 空闲超时，准备卸载")
        
        if self._backend_manager:
            try:
                await self._backend_manager.unload_model(model_id)
                print(f"[IdleMonitor] 成功卸载模型 {model_id}")
            except Exception as e:
                print(f"[IdleMonitor] 卸载模型 {model_id} 失败: {e}")
                raise
        else:
            print(f"[IdleMonitor] 警告: 未设置后端管理器，无法卸载模型")
            
    def get_all_status(self) -> Dict[int, Dict[str, Any]]:
        """获取所有监控器的状态"""
        return {port: monitor.get_status() for port, monitor in self._monitors.items()}
        
    def get_monitor(self, port: int) -> Optional[LlamaServerMonitor]:
        """获取指定端口的监控器"""
        return self._monitors.get(port)
        
    async def shutdown_all(self):
        """关闭所有监控"""
        for monitor in list(self._monitors.values()):
            await monitor.stop_monitoring()
        self._monitors.clear()


# 全局监控管理器实例
_global_idle_monitor: Optional[IdleMonitorManager] = None


def get_idle_monitor() -> IdleMonitorManager:
    """获取全局空闲监控管理器（单例）"""
    global _global_idle_monitor
    if _global_idle_monitor is None:
        _global_idle_monitor = IdleMonitorManager()
    return _global_idle_monitor


def reset_idle_monitor():
    """重置全局监控管理器（用于测试）"""
    global _global_idle_monitor
    _global_idle_monitor = None
