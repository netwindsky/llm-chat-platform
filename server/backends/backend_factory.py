from typing import Dict, Any, Optional, Type
from ..core.backend import InferenceBackend
from .llama_backend import LlamaBackend
from .sglang_backend import SGLangBackend


class BackendFactory:
    """后端工厂"""
    
    _backends: Dict[str, Type[InferenceBackend]] = {
        'llama': LlamaBackend,
        'sglang': SGLangBackend,
    }
    
    _instances: Dict[str, InferenceBackend] = {}
    
    @classmethod
    def register(cls, name: str, backend_class: Type[InferenceBackend]):
        """注册新的后端"""
        cls._backends[name.lower()] = backend_class
    
    @classmethod
    def create(cls, backend_type: str, config: Dict[str, Any]) -> InferenceBackend:
        """创建后端实例"""
        backend_type = backend_type.lower()
        
        if backend_type not in cls._backends:
            raise ValueError(
                f"Unsupported backend: {backend_type}. "
                f"Available: {list(cls._backends.keys())}"
            )
        
        if backend_type in cls._instances:
            return cls._instances[backend_type]
        
        backend = cls._backends[backend_type](config)
        cls._instances[backend_type] = backend
        
        return backend
    
    @classmethod
    def get(cls, backend_type: str) -> Optional[InferenceBackend]:
        """获取已存在的后端实例"""
        return cls._instances.get(backend_type.lower())
    
    @classmethod
    def list_available(cls) -> Dict[str, bool]:
        """列出所有可用的后端"""
        available = {}
        for name, backend_class in cls._backends.items():
            try:
                config = {"server_path": f"runtimes/{name}/bin/{name}-server.exe"}
                backend = backend_class(config)
                available[name] = backend.is_available
            except:
                available[name] = False
        return available
    
    @classmethod
    def get_or_create(cls, backend_type: str, config: Dict[str, Any]) -> InferenceBackend:
        """获取或创建后端实例"""
        backend_type = backend_type.lower()
        
        if backend_type in cls._instances:
            return cls._instances[backend_type]
        
        return cls.create(backend_type, config)
    
    @classmethod
    def close_all(cls):
        """关闭所有后端"""
        for backend in cls._instances.values():
            import asyncio
            try:
                asyncio.run(backend.shutdown())
            except:
                pass
        cls._instances.clear()
