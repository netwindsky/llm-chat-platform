from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum


class ModelStatus(Enum):
    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    ERROR = "error"


@dataclass
class ModelInfo:
    id: str
    name: str
    path: str
    type: str
    category: str
    format: str
    size: str
    quantization: str
    backend: str
    max_context: int
    default_temp: float
    default_top_p: float
    tags: List[str]
    description: str
    status: ModelStatus = ModelStatus.UNLOADED
    memory_usage: Optional[float] = None


@dataclass
class ChatMessage:
    role: str
    content: str


@dataclass
class ChatRequest:
    model: str
    messages: List[ChatMessage]
    temperature: float = 0.7
    top_p: float = 0.8
    top_k: int = 20
    max_tokens: int = 4096
    stream: bool = False
    stop: Optional[List[str]] = None


@dataclass
class ChatResponse:
    id: str
    object: str = "chat.completion"
    created: int = 0
    model: str = ""
    choices: List[Dict[str, Any]] = None
    usage: Dict[str, int] = None
    
    def __post_init__(self):
        if self.choices is None:
            self.choices = []
        if self.usage is None:
            self.usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


@dataclass
class ChatChunk:
    id: str
    object: str = "chat.completion.chunk"
    created: int = 0
    model: str = ""
    choices: List[Dict[str, Any]] = None
    usage: Dict[str, int] = None
    
    def __post_init__(self):
        if self.choices is None:
            self.choices = []
        if self.usage is None:
            self.usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


class InferenceBackend(ABC):
    """推理后端抽象基类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._model = None
        self._model_info: Optional[ModelInfo] = None
    
    @abstractmethod
    async def initialize(self, model_path: str, model_config: Dict[str, Any]) -> bool:
        """初始化模型"""
        pass
    
    @abstractmethod
    async def generate(
        self, 
        prompt: str, 
        config: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        """流式生成"""
        pass
    
    @abstractmethod
    async def chat(
        self, 
        messages: List[ChatMessage], 
        config: Dict[str, Any]
    ) -> ChatResponse:
        """对话生成（非流式）"""
        pass
    
    @abstractmethod
    async def chat_stream(
        self, 
        messages: List[ChatMessage], 
        config: Dict[str, Any]
    ) -> AsyncGenerator[ChatChunk, None]:
        """流式对话"""
        pass
    
    @abstractmethod
    async def get_model_info(self) -> Optional[ModelInfo]:
        """获取模型信息"""
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """关闭后端"""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """后端名称"""
        pass
    
    @property
    @abstractmethod
    def is_available(self) -> bool:
        """是否可用"""
        pass
    
    @property
    def is_loaded(self) -> bool:
        """模型是否已加载"""
        return self._model is not None
