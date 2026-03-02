import os
import json
import asyncio
import subprocess
import signal
from typing import AsyncGenerator, Dict, Any, Optional, List
from datetime import datetime

from ..core.backend import (
    InferenceBackend, 
    ModelInfo, 
    ChatMessage, 
    ChatResponse, 
    ChatChunk,
    ModelStatus
)


class LlamaBackend(InferenceBackend):
    """llama.cpp 后端实现"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._process: Optional[subprocess.Popen] = None
        self._server_url = config.get("server_url", "http://127.0.0.1:8080")
        self._model_path = ""
        self._model_config = {}
        self._lock = asyncio.Lock()
    
    @property
    def is_available(self) -> bool:
        """检查 llama-server 是否可用"""
        server_path = self.config.get("server_path", "runtimes/llama/bin/llama-server.exe")
        return os.path.exists(server_path)
    
    @property
    def name(self) -> str:
        return "llama"
    
    async def initialize(self, model_path: str, model_config: Dict[str, Any]) -> bool:
        """初始化模型（异步，立即返回）"""
        async with self._lock:
            # 如果已经初始化过，直接返回
            if self._process:
                return True
            
            self._model_path = model_path
            self._model_config = model_config
            
            server_path = self.config.get("server_path", "runtimes/llama/bin/llama-server.exe")
            
            if not os.path.exists(server_path):
                raise FileNotFoundError(f"llama-server not found: {server_path}")
            
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Model not found: {model_path}")
            
            ctx_size = model_config.get("max_context", 32768)
            ngl = model_config.get("gpu_layers", 99)
            
            # 使用固定端口
            port = 8081
            
            cmd = [
                server_path,
                "-m", model_path,
                "--host", "127.0.0.1",
                "--port", str(port),
                "-c", str(ctx_size),
                "-ngl", str(ngl),
                "--cont-batching"
            ]
            
            # 如果是推理模型，启用思考模式
            model_type = model_config.get("type", "language-model")
            if model_type == "reasoning-model":
                cmd.extend(["--reasoning-format", "deepseek"])
                print(f"[DEBUG] Enabling reasoning mode for {model_config.get('id', 'unknown')}")
            
            # 启动进程（不等待）
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
            )
            
            # 设置 server_url
            self._server_url = f"http://127.0.0.1:{port}"
            
            # 先设置初始状态为 loading
            print(f"initialize: setting _model_info for {model_config.get('id', 'unknown')}")
            self._model_info = ModelInfo(
                id=model_config.get("id", "unknown"),
                name=model_config.get("name", "Unknown"),
                path=model_path,
                type=model_config.get("type", "language-model"),
                category=model_config.get("category", "unknown"),
                format=model_config.get("format", "gguf"),
                size=model_config.get("size", "unknown"),
                quantization=model_config.get("quantization", "unknown"),
                backend="llama",
                max_context=ctx_size,
                default_temp=model_config.get("default_temp", 0.7),
                default_top_p=model_config.get("default_top_p", 0.8),
                tags=model_config.get("tags", []),
                description=model_config.get("description", ""),
                status=ModelStatus.LOADING  # 设置为加载中
            )
            print(f"initialize: _model_info set, status={self._model_info.status}")
            
            # 创建后台任务等待服务器启动
            asyncio.create_task(self._wait_and_set_status())
            
            # 立即返回 True（模型状态为 loading）
            return True
    
    async def _wait_and_set_status(self):
        """后台等待服务器启动并更新状态"""
        try:
            print(f"_wait_and_set_status: waiting for {self._model_info.id if self._model_info else 'unknown'}")
            await self._wait_for_server(120)  # 最多等待 120 秒
            
            # 服务器启动成功，只更新状态字段
            print(f"_wait_and_set_status: server ready, updating status")
            if self._model_info:
                self._model_info.status = ModelStatus.LOADED
            print(f"Model {self._model_info.name if self._model_info else 'unknown'} fully loaded and ready")
        except TimeoutError as e:
            print(f"Model loading timeout: {e}")
            self._process = None
            if self._model_info:
                self._model_info.status = ModelStatus.ERROR
    
    async def _wait_for_server(self, timeout: int = 30) -> bool:
        """等待服务器启动"""
        import httpx
        
        print(f"_wait_for_server: waiting for {self._server_url} (timeout={timeout}s)")
        start_time = datetime.now()
        while (datetime.now() - start_time).seconds < timeout:
            try:
                async with httpx.AsyncClient() as client:
                    # 先检查健康端点
                    health_response = await client.get(f"{self._server_url}/health", timeout=2.0)
                    if health_response.status_code == 200:
                        # 健康检查通过，再测试聊天端点是否可用
                        test_response = await client.post(
                            f"{self._server_url}/v1/chat/completions",
                            json={"messages": [{"role": "user", "content": ""}], "max_tokens": 1},
                            timeout=5.0
                        )
                        if test_response.status_code == 200:
                            elapsed = (datetime.now() - start_time).seconds
                            print(f"_wait_for_server: server ready after {elapsed}s")
                            return True
            except Exception as e:
                pass
            await asyncio.sleep(1)
        
        elapsed = (datetime.now() - start_time).seconds
        print(f"_wait_for_server: timeout after {elapsed}s")
        raise TimeoutError("Server failed to start within timeout")
    
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
                "max_tokens": config.get("max_tokens", 4096),
                "stream": True
            }
            
            async with client.stream(
                "POST",
                f"{self._server_url}/v1/completions",
                json=payload,
                timeout=120.0
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
        from time import time
        
        start_time = time()
        
        payload = {
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": config.get("temperature", 0.7),
            "top_p": config.get("top_p", 0.8),
            "top_k": config.get("top_k", 20),
            "max_tokens": config.get("max_tokens", 4096),
            "stream": False
        }
        
        # 重试逻辑：如果模型正在加载，等待并重试
        max_retries = 10
        retry_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient() as client:
                    print(f"llama_backend.chat: sending request to {self._server_url}/v1/chat/completions")
                    response = await client.post(
                        f"{self._server_url}/v1/chat/completions",
                        json=payload,
                        timeout=180.0
                    )
                    print(f"llama_backend.chat: response status={response.status_code}, content={response.text[:200]}")
                    result = response.json()
                    
                    # 检查是否是 503 错误（模型加载中）
                    if 'error' in result and result['error'].get('code') == 503:
                        if attempt < max_retries - 1:
                            print(f"Model loading, retrying in {retry_delay}s... (attempt {attempt + 1}/{max_retries})")
                            await asyncio.sleep(retry_delay)
                            continue
                        else:
                            raise Exception("Model loading timeout. Please try again later.")
                    
                    print(f"llama-server response: {result}")
                    
                    end_time = time()
                    
                    content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                    usage = result.get("usage", {})
                    
                    # deepseek 格式的思考内容在 reasoning_content 字段
                    thinking = result.get("choices", [{}])[0].get("message", {}).get("reasoning_content", "")
                    
                    return ChatResponse(
                        id=result.get("id", "chatcmpl-unknown"),
                        created=result.get("created", int(start_time)),
                        model=result.get("model", self._model_info.name if self._model_info else "unknown"),
                        choices=[{
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": content,
                                "thinking": thinking
                            },
                            "finish_reason": result.get("choices", [{}])[0].get("finish_reason", "stop")
                        }],
                        usage={
                            "prompt_tokens": usage.get("prompt_tokens", 0),
                            "completion_tokens": usage.get("completion_tokens", 0),
                            "total_tokens": usage.get("total_tokens", 0)
                        }
                    )
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"Request failed, retrying in {retry_delay}s... (attempt {attempt + 1}/{max_retries}): {e}")
                    await asyncio.sleep(retry_delay)
                else:
                    raise e
        
        raise Exception("Failed to get response after all retries")
    
    async def chat_stream(
        self, 
        messages: List[ChatMessage], 
        config: Dict[str, Any]
    ) -> AsyncGenerator[ChatChunk, None]:
        """流式对话"""
        import httpx
        from time import time
        
        start_time = time()
        
        payload = {
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": config.get("temperature", 0.7),
            "top_p": config.get("top_p", 0.8),
            "top_k": config.get("top_k", 20),
            "max_tokens": config.get("max_tokens", 4096),
            "stream": True
        }
        
        # 用于累积思考内容
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self._server_url}/v1/chat/completions",
                json=payload,
                timeout=180.0
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
                            
                            # deepseek 格式的思考内容在 reasoning_content 字段
                            thinking = delta.get("reasoning_content", "")
                            
                            yield ChatChunk(
                                id=chunk_data.get("id", "chatcmpl-stream"),
                                created=chunk_data.get("created", int(start_time)),
                                model=chunk_data.get("model", self._model_info.name if self._model_info else "unknown"),
                                choices=[{
                                    "index": 0,
                                    "delta": {
                                        "content": content,
                                        "thinking": thinking
                                    },
                                    "finish_reason": chunk_data.get("choices", [{}])[0].get("finish_reason")
                                }]
                            )
                        except Exception as e:
                            print(f"Error processing chunk: {e}")
                            pass
    
    async def get_model_info(self) -> Optional[ModelInfo]:
        """获取模型信息"""
        return self._model_info
    
    async def shutdown(self) -> None:
        """关闭后端"""
        async with self._lock:
            if self._process:
                try:
                    if os.name == 'nt':
                        os.kill(self._process.pid, signal.CTRL_BREAK_EVENT)
                    else:
                        self._process.terminate()
                    self._process.wait(timeout=5)
                except:
                    self._process.kill()
                self._process = None
            
            self._model_info = None
