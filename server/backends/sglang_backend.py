"""SGLang 后端实现"""
import os
import json
import asyncio
from typing import AsyncGenerator, Dict, Any, Optional, List
from dataclasses import dataclass

from ..core.backend import (
    InferenceBackend,
    ModelInfo,
    ChatMessage,
    ChatResponse,
    ChatChunk,
    ModelStatus
)


class SGLangBackend(InferenceBackend):
    """SGLang 推理后端"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._process = None
        self._server_url = None
        self._lock = asyncio.Lock()
    
    async def initialize(self, model_path: str, model_config: Dict[str, Any]) -> bool:
        """初始化模型"""
        # SGLang 后端实现
        self._model_info = ModelInfo(
            id=model_config.get("id", "unknown"),
            name=model_config.get("name", "Unknown"),
            path=model_path,
            type=model_config.get("type", "language-model"),
            category=model_config.get("category", "unknown"),
            format=model_config.get("format", "gguf"),
            size=model_config.get("size", "unknown"),
            quantization=model_config.get("quantization", "unknown"),
            backend="sglang",
            max_context=model_config.get("max_context", 32768),
            default_temp=model_config.get("default_temp", 0.7),
            default_top_p=model_config.get("default_top_p", 0.8),
            tags=model_config.get("tags", []),
            description=model_config.get("description", ""),
            status=ModelStatus.LOADING
        )
        return True
    
    async def generate(
        self, 
        prompt: str, 
        config: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        """流式生成"""
        import httpx
        
        async with httpx.AsyncClient() as client:
            payload = {
                "prompt": prompt,
                "temperature": config.get("temperature", 0.7),
                "top_p": config.get("top_p", 0.8),
                "top_k": config.get("top_k", 20),
                "max_tokens": config.get("max_tokens", 131072),
                "stream": True
            }
            
            async with client.stream(
                "POST",
                f"{self._server_url}/v1/completions",
                json=payload,
                timeout=None
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            if "content" in chunk.get("choices", [{}])[0]:
                                yield chunk["choices"][0]["content"]
                        except:
                            pass
    
    async def chat(
        self, 
        messages: List[ChatMessage], 
        config: Dict[str, Any]
    ) -> ChatResponse:
        """对话生成（非流式）"""
        import httpx
        
        payload = {
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": config.get("temperature", 0.7),
            "top_p": config.get("top_p", 0.8),
            "top_k": config.get("top_k", 20),
            "max_tokens": config.get("max_tokens", 131072),
            "stream": False
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._server_url}/v1/chat/completions",
                json=payload,
                timeout=180.0
            )
            result = response.json()
            
            message = result.get("choices", [{}])[0].get("message", {})
            content = message.get("content", "")
            usage = result.get("usage", {})
            
            return ChatResponse(
                id=result.get("id", "chatcmpl-sglang"),
                object="chat.completion",
                created=result.get("created", 0),
                model=result.get("model", self._model_info.name if self._model_info else "unknown"),
                choices=[{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": content
                    },
                    "finish_reason": result.get("choices", [{}])[0].get("finish_reason", "stop")
                }],
                usage={
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0)
                }
            )
    
    async def chat_stream(
        self, 
        messages: List[ChatMessage], 
        config: Dict[str, Any]
    ) -> AsyncGenerator[ChatChunk, None]:
        """流式对话生成"""
        import httpx
        from time import time
        
        start_time = time()
        
        payload = {
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": config.get("temperature", 0.7),
            "top_p": config.get("top_p", 0.8),
            "top_k": config.get("top_k", 20),
            "max_tokens": config.get("max_tokens", 131072),
            "stream": True
        }
        
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self._server_url}/v1/chat/completions",
                json=payload,
                timeout=None
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk_data = json.loads(data)
                            delta = chunk_data.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            
                            yield ChatChunk(
                                id=chunk_data.get("id", "chatcmpl-sglang"),
                                object="chat.completion.chunk",
                                created=chunk_data.get("created", int(start_time)),
                                model=chunk_data.get("model", self._model_info.name if self._model_info else "unknown"),
                                choices=[{
                                    "index": 0,
                                    "delta": {
                                        "content": content,
                                        "thinking": ""
                                    },
                                    "finish_reason": chunk_data.get("choices", [{}])[0].get("finish_reason")
                                }]
                            )
                        except:
                            pass
    
    async def get_model_info(self) -> Optional[ModelInfo]:
        """获取模型信息"""
        return self._model_info
    
    async def shutdown(self) -> None:
        """关闭后端"""
        if self._process:
            self._process.terminate()
            self._process = None
        self._model_info = None
    
    async def health_check(self) -> bool:
        """健康检查"""
        return True
    
    async def ensure_running(self) -> bool:
        """确保服务正在运行"""
        return True
