import os
import yaml
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ModelConfig:
    """模型配置"""
    id: str
    name: str
    path: str
    type: str = "language-model"
    category: str = "unknown"
    format: str = "gguf"
    size: str = "unknown"
    quantization: str = "unknown"
    backend: str = "llama"
    max_context: int = 32768
    default_temp: float = 0.7
    default_top_p: float = 0.8
    default_top_k: int = 20
    default_max_tokens: int = 131072
    min_p: Optional[float] = None
    presence_penalty: Optional[float] = None
    repetition_penalty: Optional[float] = None
    repeat_penalty: Optional[float] = None
    enable_thinking: Optional[bool] = None
    parallel: int = 1
    batch_size: int = 2048
    ubatch_size: Optional[int] = None
    gpu_layers: int = 99
    ncmoe: Optional[int] = None
    threads: Optional[int] = None
    cpu_range: Optional[str] = None
    cache_type_k: Optional[str] = None
    cache_type_v: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    description: str = ""
    status: str = "unloaded"
    memory_usage: Optional[float] = None
    file_exists: bool = False
    mmproj: Optional[str] = None


@dataclass
class ModelTypeConfig:
    """模型类型配置"""
    icon: str = "📦"
    color: str = "#666666"
    description: str = ""


class ModelManager:
    """模型管理器"""
    
    def __init__(self, config_path: str = "configs/models.yaml"):
        self.config_path = config_path
        self.config_dir = os.path.dirname(os.path.abspath(config_path))
        self.models: Dict[str, ModelConfig] = {}
        self.model_types: Dict[str, ModelTypeConfig] = {}
        self._load_config()
    
    def _resolve_path(self, path: Optional[str]) -> Optional[str]:
        """将相对路径转换为绝对路径"""
        if not path:
            return None
        if os.path.isabs(path):
            return path
        # 路径现在已经是相对于 models/ 目录的，需要加上 models/ 前缀
        return os.path.normpath(os.path.join(self.config_dir, '..', 'models', path))
    
    def _load_config(self):
        """加载配置文件"""
        if not os.path.exists(self.config_path):
            self._create_default_config()
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 加载模型
        for m in config.get('models', []):
            model_path = self._resolve_path(m.get('path', ''))
            mmproj_path = self._resolve_path(m.get('mmproj'))
            
            # 跳过没有 path 的模型配置
            if not model_path:
                print(f"[ModelManager] Warning: Model {m.get('id', 'unknown')} has no path, skipping")
                continue
            
            model = ModelConfig(
                id=m.get('id', ''),
                name=m.get('name', ''),
                path=model_path,
                type=m.get('type', 'language-model'),
                category=m.get('category', 'unknown'),
                format=m.get('format', 'gguf'),
                size=m.get('size', 'unknown'),
                quantization=m.get('quantization', 'unknown'),
                backend=m.get('backend', 'llama'),
                max_context=m.get('max_context', 32768),
                default_temp=m.get('default_temp', 0.7),
                default_top_p=m.get('default_top_p', 0.8),
                default_top_k=m.get('default_top_k', 20),
                default_max_tokens=m.get('default_max_tokens', 131072),
                presence_penalty=m.get('presence_penalty'),
                repetition_penalty=m.get('repetition_penalty'),
                enable_thinking=m.get('enable_thinking'),
                parallel=m.get('parallel', 1),
                batch_size=m.get('batch_size', 512),
                ubatch_size=m.get('ubatch_size'),
                gpu_layers=m.get('gpu_layers', 99),
                ncmoe=m.get('ncmoe'),
                threads=m.get('threads'),
                cpu_range=m.get('cpu_range'),
                cache_type_k=m.get('cache_type_k'),
                cache_type_v=m.get('cache_type_v'),
                tags=m.get('tags', []),
                description=m.get('description', ''),
                mmproj=mmproj_path
            )
            # 检查文件是否存在
            model.file_exists = os.path.exists(model.path)
            self.models[model.id] = model
        
        # 加载模型类型
        for mt, cfg in config.get('model_types', {}).items():
            self.model_types[mt] = ModelTypeConfig(
                icon=cfg.get('icon', '📦'),
                color=cfg.get('color', '#666666'),
                description=cfg.get('description', '')
            )
    
    def _create_default_config(self):
        """创建默认配置"""
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        default_config = {
            'models': [],
            'model_types': {
                'language-model': {'icon': '💬', 'color': '#3b82f6', 'description': '大语言模型'},
                'vision-language-model': {'icon': '👁️', 'color': '#8b5cf6', 'description': '视觉语言模型'},
                'code-model': {'icon': '💻', 'color': '#10b981', 'description': '代码专用模型'},
                'reasoning-model': {'icon': '🧠', 'color': '#f59e0b', 'description': '推理强化模型'},
                'embedding-model': {'icon': '📊', 'color': '#ec4899', 'description': '嵌入向量模型'}
            }
        }
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(default_config, f, allow_unicode=True)
    
    def get_model(self, model_id: str) -> Optional[ModelConfig]:
        """获取模型配置"""
        return self.models.get(model_id)
    
    def list_models(
        self, 
        model_type: Optional[str] = None,
        category: Optional[str] = None,
        loaded_only: bool = False
    ) -> List[ModelConfig]:
        """列出模型"""
        models = list(self.models.values())
        
        if model_type:
            models = [m for m in models if m.type == model_type]
        
        if category:
            models = [m for m in models if m.category == category]
        
        if loaded_only:
            models = [m for m in models if m.status == "loaded"]
        
        return models
    
    def get_models_by_type(self) -> Dict[str, List[ModelConfig]]:
        """按类型分组获取模型"""
        result = {}
        for model in self.models.values():
            if model.type not in result:
                result[model.type] = []
            result[model.type].append(model)
        return result
    
    def get_types(self) -> Dict[str, ModelTypeConfig]:
        """获取所有模型类型"""
        return self.model_types
    
    def update_model_status(self, model_id: str, status: str, memory_usage: Optional[float] = None):
        """更新模型状态"""
        if model_id in self.models:
            self.models[model_id].status = status
            self.models[model_id].memory_usage = memory_usage
    
    def reload(self):
        """重新加载配置"""
        self._load_config()


# 全局模型管理器实例（用于适配器访问）
_global_model_manager: Optional[ModelManager] = None


def set_global_model_manager(manager: ModelManager):
    """设置全局模型管理器"""
    global _global_model_manager
    _global_model_manager = manager


def get_model_manager() -> Optional[ModelManager]:
    """获取全局模型管理器"""
    return _global_model_manager
