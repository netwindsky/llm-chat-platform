import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from ..backends.backend_factory import BackendFactory
from ..core.backend import ChatMessage, InferenceBackend
from .idle_monitor import get_idle_monitor


class BackendManager:
    """后端管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._loaded_models: Dict[str, InferenceBackend] = {}
        self._current_model: Optional[str] = None
        self._lock = asyncio.Lock()
        
        # 获取或创建空闲监控管理器
        self._idle_monitor = get_idle_monitor()
        self._idle_monitor.set_backend_manager(self)
        
        # 从配置中读取空闲监控设置
        idle_config = config.get("idle_monitor", {})
        self._default_idle_timeout = idle_config.get("timeout", 60)  # 默认60秒
        self._idle_monitor_enabled = idle_config.get("enabled", True)  # 默认启用
        
        # 调试日志
        print(f"[BackendManager] 空闲监控配置: enabled={self._idle_monitor_enabled}, timeout={self._default_idle_timeout}")
        print(f"[BackendManager] 完整 idle_config: {idle_config}")
    
    async def load_model(self, model_id: str, model_path: str, model_config: Dict[str, Any]) -> bool:
        """加载模型"""
        print(f"load_model: starting for {model_id}")
        
        # 获取新模型的 max_context
        new_max_context = model_config.get("max_context", 32768)
        
        # 先检查是否已加载且进程仍在运行
        if model_id in self._loaded_models:
            backend = self._loaded_models[model_id]
            if hasattr(backend, 'is_running') and backend.is_running:
                print(f"load_model: already loaded and running {model_id}")
                return True
            else:
                print(f"load_model: model {model_id} in dict but process not running, cleaning up")
                del self._loaded_models[model_id]
                if self._current_model == model_id:
                    self._current_model = None
        
        # 先确定需要卸载哪些模型（在锁内）
        async with self._lock:
            models_to_unload = []
            
            # 检查当前模型的 max_context 是否与新模型相同
            need_restart = False
            if self._current_model and self._current_model != model_id:
                current_backend = self._loaded_models.get(self._current_model)
                if current_backend:
                    current_model_info = await current_backend.get_model_info()
                    if current_model_info:
                        current_max_context = current_model_info.max_context
                        if current_max_context != new_max_context:
                            print(f"load_model: max_context changed from {current_max_context} to {new_max_context}, need restart")
                            need_restart = True
                
                # 如果 max_context 不同，需要重启 llama-server，卸载当前模型
                if need_restart:
                    models_to_unload.append(self._current_model)
                
                models_to_unload.append(self._current_model)
            
            # 检查是否已达到最大加载数量
            max_models = self.config.get("model_loading", {}).get("max_loaded_models", 1)
            if len(self._loaded_models) >= max_models and model_id not in self._loaded_models:
                oldest_model = next(iter(self._loaded_models))
                if oldest_model not in models_to_unload:
                    models_to_unload.append(oldest_model)
        
        # 先卸载旧模型（在锁外，避免死锁）
        for model_to_unload in models_to_unload:
            print(f"load_model: unloading {model_to_unload} first")
            await self._unload_model_no_lock(model_to_unload)
        
        # 创建后端实例（在锁外）
        backend_type = model_config.get("backend", "llama")
        model_type = model_config.get("type", "language-model")
        print(f"load_model: model_config type={model_type}, backend={backend_type}")
        backend_config = {
            "server_path": f"runtimes/{backend_type}/bin/{backend_type}-server.exe"
        }
        
        # 从模型配置中获取端口，如果未指定则使用默认值
        port = model_config.get("port", 38521)
        print(f"load_model: creating backend for {model_id} with port={port}")
        backend = BackendFactory.create(backend_type, backend_config, port)
        
        # 初始化模型（在锁外，耗时操作）
        print(f"load_model: initializing backend for {model_id} with type={model_type}")
        success = await backend.initialize(model_path, model_config)
        print(f"load_model: initialization {'success' if success else 'failed'} for {model_id}")
        
        # 注册到字典
        async with self._lock:
            if success:
                self._loaded_models[model_id] = backend
                self._current_model = model_id
                
                # 注册到空闲监控
                if self._idle_monitor_enabled:
                    # 从模型配置中获取监控设置（模型配置可以覆盖全局设置）
                    model_idle_timeout = model_config.get("idle_timeout", self._default_idle_timeout)
                    # 模型级别的 enabled 默认使用全局设置，如果模型明确指定则使用模型配置
                    model_idle_enabled = model_config.get("idle_monitor_enabled", self._idle_monitor_enabled)
                    
                    self._idle_monitor.register_server(
                        port=port,
                        idle_timeout=model_idle_timeout,
                        enabled=model_idle_enabled
                    )
                    self._idle_monitor.set_model_for_port(port, model_id)
                    print(f"load_model: 已注册空闲监控 - 端口 {port}, 超时 {model_idle_timeout}秒, 启用 {model_idle_enabled}")
        
        return success
    
    async def _unload_model_no_lock(self, model_id: str) -> bool:
        """卸载模型（内部方法，不获取锁）"""
        # 直接操作字典，不再次获取锁
        if model_id in self._loaded_models:
            backend = self._loaded_models[model_id]
            await backend.shutdown()
            del self._loaded_models[model_id]
            
            if self._current_model == model_id:
                self._current_model = next(iter(self._loaded_models)) if self._loaded_models else None
            
            return True
        return False
    
    async def unload_model(self, model_id: str) -> bool:
        """卸载模型"""
        async with self._lock:
            if model_id not in self._loaded_models:
                return True
            
            backend = self._loaded_models[model_id]
            await backend.shutdown()
            
            del self._loaded_models[model_id]
            
            if self._current_model == model_id:
                self._current_model = next(iter(self._loaded_models)) if self._loaded_models else None
            
            return True
    
    async def chat(self, model_id: str, messages: List[ChatMessage], config: Dict[str, Any]):
        """对话生成"""
        if model_id not in self._loaded_models:
            raise ValueError(f"Model not loaded: {model_id}")
        
        backend = self._loaded_models[model_id]
        
        # 检查进程是否在运行
        if hasattr(backend, 'is_running') and not backend.is_running:
            print(f"chat: process not running for {model_id}, removing from loaded models")
            del self._loaded_models[model_id]
            if self._current_model == model_id:
                self._current_model = None
            raise ValueError(f"Model process not running: {model_id}")
        
        # 更新空闲监控的最后请求时间
        if hasattr(backend, 'port'):
            self._idle_monitor.update_request_time(backend.port)
        
        try:
            result = await backend.chat(messages, config)
            return result
        except Exception as e:
            # 如果调用失败，检查进程是否还在运行
            if hasattr(backend, 'is_running') and not backend.is_running:
                print(f"chat: process crashed for {model_id}, removing from loaded models")
                del self._loaded_models[model_id]
                if self._current_model == model_id:
                    self._current_model = None
            raise
    
    async def chat_stream(self, model_id: str, messages: List[ChatMessage], config: Dict[str, Any]):
        """流式对话生成"""
        if model_id not in self._loaded_models:
            raise ValueError(f"Model not loaded: {model_id}")
        
        backend = self._loaded_models[model_id]
        
        # 检查进程是否在运行
        if hasattr(backend, 'is_running') and not backend.is_running:
            print(f"chat_stream: process not running for {model_id}, removing from loaded models")
            del self._loaded_models[model_id]
            if self._current_model == model_id:
                self._current_model = None
            raise ValueError(f"Model process not running: {model_id}")
        
        # 更新空闲监控的最后请求时间
        if hasattr(backend, 'port'):
            self._idle_monitor.update_request_time(backend.port)
        
        try:
            async for chunk in backend.chat_stream(messages, config):
                yield chunk
        except Exception as e:
            # 如果调用失败，检查进程是否还在运行
            if hasattr(backend, 'is_running') and not backend.is_running:
                print(f"chat_stream: process crashed for {model_id}, removing from loaded models")
                del self._loaded_models[model_id]
                if self._current_model == model_id:
                    self._current_model = None
            raise
    
    def get_loaded_models(self) -> List[str]:
        """获取已加载的模型列表（只返回进程仍在运行的模型）"""
        running_models = []
        for model_id, backend in self._loaded_models.items():
            if hasattr(backend, 'is_running') and backend.is_running:
                running_models.append(model_id)
            elif not hasattr(backend, 'is_running'):
                running_models.append(model_id)
        return running_models
    
    def get_current_model(self) -> Optional[str]:
        """获取当前模型（只返回进程仍在运行的模型）"""
        if self._current_model and self._current_model in self._loaded_models:
            backend = self._loaded_models[self._current_model]
            if hasattr(backend, 'is_running') and not backend.is_running:
                return None
        return self._current_model
    
    async def set_current_model(self, model_id: str) -> bool:
        """设置当前模型"""
        async with self._lock:
            if model_id not in self._loaded_models:
                return False
            self._current_model = model_id
            return True
    
    async def shutdown(self):
        """关闭所有模型"""
        for model_id in list(self._loaded_models.keys()):
            await self.unload_model(model_id)


# 全局后端管理器实例
_global_backend_manager: Optional[BackendManager] = None


def set_global_backend_manager(manager: BackendManager):
    """设置全局后端管理器"""
    global _global_backend_manager
    _global_backend_manager = manager


def get_backend_manager() -> Optional[BackendManager]:
    """获取全局后端管理器"""
    return _global_backend_manager
