"""
Embedding 后端实现
支持本地模型、API 调用和 GGUF 格式（llama.cpp）
"""

import os
import json
import numpy as np
from typing import List, Dict, Any, Optional
from pathlib import Path


class EmbeddingBackend:
    """Embedding 后端基类"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self._model = None
        self._tokenizer = None

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """生成文本嵌入向量"""
        raise NotImplementedError

    async def initialize(self, model_path: str = None) -> bool:
        """初始化模型"""
        raise NotImplementedError


class LocalEmbeddingBackend(EmbeddingBackend):
    """本地 Embedding 模型后端（使用 sentence-transformers）"""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self._model_name = config.get("model", "all-MiniLM-L6-v2")
        self._dimension = config.get("dimension", 384)

    async def initialize(self, model_path: str = None) -> bool:
        """初始化本地模型"""
        try:
            # 尝试使用 sentence-transformers
            from sentence_transformers import SentenceTransformer

            if model_path and os.path.exists(model_path):
                self._model = SentenceTransformer(model_path)
            else:
                self._model = SentenceTransformer(self._model_name)

            print(f"[EmbeddingBackend] Loaded model: {self._model_name}")
            return True

        except ImportError:
            print("[EmbeddingBackend] sentence-transformers not installed, using fallback")
            return await self._init_fallback()

        except Exception as e:
            print(f"[EmbeddingBackend] Failed to load model: {e}")
            return await self._init_fallback()

    async def _init_fallback(self) -> bool:
        """初始化备用方案（简单的哈希嵌入）"""
        print("[EmbeddingBackend] Using fallback embedding (random vectors)")
        return True

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """生成嵌入向量"""
        if self._model:
            # 使用真实模型
            embeddings = self._model.encode(texts, convert_to_numpy=True)
            return embeddings.tolist()
        else:
            # 备用方案：返回基于文本哈希的伪随机向量
            # 注意：这不是真正的语义嵌入，仅用于测试
            return self._fallback_embed(texts)

    def _fallback_embed(self, texts: List[str]) -> List[List[float]]:
        """备用嵌入方案（基于哈希的确定性伪随机向量）"""
        np.random.seed(42)  # 固定种子以保证可重复性
        embeddings = []

        for text in texts:
            # 使用文本哈希作为种子
            seed = hash(text) % (2**32)
            np.random.seed(seed)
            embedding = np.random.randn(self._dimension).astype(np.float32)
            # 归一化
            embedding = embedding / np.linalg.norm(embedding)
            embeddings.append(embedding.tolist())

        return embeddings


class LlamaEmbeddingBackend(EmbeddingBackend):
    """使用 llama.cpp 加载 GGUF 格式的 Embedding 模型"""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self._model_path = config.get("model_path", "")
        self._dimension = config.get("dimension", 1024)  # Snowflake Arctic Embed L 默认 1024 维
        self._max_context = config.get("max_context", 512)
        self._llama = None

    async def initialize(self, model_path: str = None) -> bool:
        """初始化 llama.cpp 模型"""
        try:
            # 尝试使用 llama-cpp-python
            from llama_cpp import Llama

            path = model_path or self._model_path
            if not path or not os.path.exists(path):
                raise FileNotFoundError(f"Model file not found: {path}")

            print(f"[LlamaEmbeddingBackend] Loading GGUF model: {path}")

            # 加载模型（embedding 模式）
            self._llama = Llama(
                model_path=path,
                n_ctx=self._max_context,
                embedding=True,  # 启用嵌入模式
                verbose=False
            )

            # 获取实际的嵌入维度
            self._dimension = self._llama.n_embd()

            print(f"[LlamaEmbeddingBackend] Model loaded, dimension: {self._dimension}")
            return True

        except ImportError:
            print("[LlamaEmbeddingBackend] llama-cpp-python not installed")
            return False

        except Exception as e:
            print(f"[LlamaEmbeddingBackend] Failed to load model: {e}")
            return False

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """使用 llama.cpp 生成嵌入向量"""
        if self._llama is None:
            raise RuntimeError("Model not initialized")

        embeddings = []
        for text in texts:
            try:
                # 生成嵌入
                # llama-cpp-python 的 embed 方法返回向量
                embedding = self._llama.embed(text)
                embeddings.append(embedding)
            except Exception as e:
                print(f"[LlamaEmbeddingBackend] Error embedding text: {e}")
                # 返回零向量作为后备
                embeddings.append([0.0] * self._dimension)

        return embeddings


class APIEmbeddingBackend(EmbeddingBackend):
    """通过 API 调用外部 Embedding 服务"""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self._api_url = config.get("api_url", "")
        self._api_key = config.get("api_key", "")
        self._model = config.get("model", "text-embedding-3-small")

    async def initialize(self, model_path: str = None) -> bool:
        """API 后端不需要本地初始化"""
        return True

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """通过 API 获取嵌入向量"""
        import httpx

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "input": texts,
            "model": self._model
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self._api_url,
                headers=headers,
                json=payload,
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()

            # 提取嵌入向量
            embeddings = []
            for item in data.get("data", []):
                embeddings.append(item["embedding"])

            return embeddings


class EmbeddingManager:
    """Embedding 管理器"""

    _instance = None
    _backend: Optional[EmbeddingBackend] = None
    _config: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def initialize(self, config: Dict[str, Any] = None):
        """初始化 Embedding 后端"""
        config = config or {}
        backend_type = config.get("type", "local")
        model_format = config.get("format", "pytorch")  # pytorch, gguf, api

        self._config = config

        # 根据格式选择后端
        if backend_type == "api":
            self._backend = APIEmbeddingBackend(config)
        elif model_format == "gguf":
            self._backend = LlamaEmbeddingBackend(config)
        else:
            self._backend = LocalEmbeddingBackend(config)

        return await self._backend.initialize(config.get("model_path"))

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """生成嵌入向量"""
        if self._backend is None:
            # 自动初始化（使用默认配置）
            await self.initialize()

        return await self._backend.embed(texts)

    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._backend is not None

    def get_config(self) -> Dict[str, Any]:
        """获取当前配置"""
        return self._config


# 全局管理器实例
_embedding_manager = EmbeddingManager()


async def get_embeddings(texts: List[str], model: str = None) -> List[List[float]]:
    """获取文本嵌入向量的便捷函数"""
    return await _embedding_manager.embed(texts)


async def initialize_embedding_backend(config: Dict[str, Any] = None):
    """初始化 Embedding 后端"""
    return await _embedding_manager.initialize(config)


def get_embedding_manager() -> EmbeddingManager:
    """获取 Embedding 管理器实例"""
    return _embedding_manager
