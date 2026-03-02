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
    tags: List[str] = field(default_factory=list)
    description: str = ""
    status: str = "unloaded"
    memory_usage: Optional[float] = None
    file_exists: bool = False


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
        self.models: Dict[str, ModelConfig] = {}
        self.model_types: Dict[str, ModelTypeConfig] = {}
        self._load_config()
    
    def _load_config(self):
        """加载配置文件"""
        if not os.path.exists(self.config_path):
            self._create_default_config()
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 加载模型
        for m in config.get('models', []):
            model = ModelConfig(
                id=m.get('id', ''),
                name=m.get('name', ''),
                path=m.get('path', ''),
                type=m.get('type', 'language-model'),
                category=m.get('category', 'unknown'),
                format=m.get('format', 'gguf'),
                size=m.get('size', 'unknown'),
                quantization=m.get('quantization', 'unknown'),
                backend=m.get('backend', 'llama'),
                max_context=m.get('max_context', 32768),
                default_temp=m.get('default_temp', 0.7),
                default_top_p=m.get('default_top_p', 0.8),
                tags=m.get('tags', []),
                description=m.get('description', '')
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
