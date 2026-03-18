import os
import json
import asyncio
import subprocess
import signal
import re
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
from ..utils.http_client import HttpClient


def parse_tool_calls(content: str) -> Optional[List[Dict[str, Any]]]:
    """从 content 中解析 tool_calls
    
    支持的格式:
    1. <tool_call> <function=function_name> <parameter=value> ... </tool_call>
    2. task(agent="...", description="...", ...)
    """
    tool_calls = []
    
    # 匹配 <tool_call> 格式
    tool_call_pattern = r'<tool_call>\s*<(\w+)=([^>]+)>\s*(.*?)</tool_call>'
    matches = re.findall(tool_call_pattern, content, re.DOTALL)
    
    for match in matches:
        func_type, func_name, params_str = match
        # 解析参数
        params = {}
        param_pattern = r'<(\w+)>\s*(.*?)\s*</\w+>'
        for pmatch in re.findall(param_pattern, params_str):
            params[pmatch[0]] = pmatch[1].strip()
        
        tool_calls.append({
            "id": f"call_{len(tool_calls)}",
            "type": "function",
            "function": {
                "name": func_name.strip(),
                "arguments": json.dumps(params) if params else "{}"
            }
        })
    
    # 匹配 task(...) 格式
    task_pattern = r'task\((.*?)\)(?!\s*\w)'
    for match in re.finditer(task_pattern, content, re.DOTALL):
        args_str = match.group(1)
        # 解析 task 参数
        args = {}
        # 匹配 key=value 对
        kv_pattern = r'(\w+)\s*=\s*("[^"]*"|\[[^\]]*\]|[^,\)]+)'
        for kv in re.findall(kv_pattern, args_str):
            key, value = kv
            value = value.strip().strip('"')
            args[key] = value
        
        if args:
            tool_calls.append({
                "id": f"call_{len(tool_calls)}",
                "type": "function", 
                "function": {
                    "name": "task",
                    "arguments": json.dumps(args)
                }
            })
    
    return tool_calls if tool_calls else None


class LlamaBackend(InferenceBackend):
    """llama.cpp 后端实现"""
    
    def __init__(self, config: Dict[str, Any], port: int = 38521):
        super().__init__(config)
        self._process: Optional[subprocess.Popen] = None
        self._port = port
        self._server_url = f"http://127.0.0.1:{port}"
        self._model_path = ""
        self._model_config = {}
        self._lock = asyncio.Lock()
    
    @property
    def port(self) -> int:
        """获取服务端口号"""
        return self._port
    
    @property
    def is_available(self) -> bool:
        """检查 llama-server 是否可用"""
        server_path = self.config.get("server_path", "runtimes/llama/bin/llama-server.exe")
        return os.path.exists(server_path)
    
    @property
    def is_running(self) -> bool:
        """检查进程是否还在运行"""
        if self._process is None:
            return False
        return self._process.poll() is None
    
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
            
            # 获取项目根目录 (LLM 目录)
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
            server_path = self.config.get("server_path", "runtimes/llama/bin/llama-server.exe")
            
            if not os.path.exists(server_path):
                raise FileNotFoundError(f"llama-server not found: {server_path}")
            
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Model not found: {model_path}")
            
            # 将绝对路径转换为相对路径
            def to_relative(path):
                if os.path.isabs(path):
                    return os.path.relpath(path, project_root)
                return path
            
            model_path_rel = to_relative(model_path)
            
            ctx_size = model_config.get("max_context", 32768)
            ngl = model_config.get("gpu_layers", 99)
            parallel = model_config.get("parallel", 1)
            batch_size = model_config.get("batch_size", 2048)
            ubatch_size = model_config.get("ubatch_size") or batch_size
            
            port = model_config.get("port", self._port)
            
            cmd = [
                server_path,
                "-m", model_path_rel,
                "--host", "127.0.0.1",
                "--port", str(port),
                "-c", str(ctx_size),
                "-ngl", str(ngl),
                "-np", str(parallel),
                "-b", str(batch_size),
                "-ub", str(ubatch_size),
                "-fa", "on",
                "--cont-batching"
            ]
            
            # 添加 KV Cache 量化参数
            cache_type_k = model_config.get("cache_type_k")
            cache_type_v = model_config.get("cache_type_v")
            if cache_type_k:
                cmd.extend(["--cache-type-k", cache_type_k])
            if cache_type_v:
                cmd.extend(["--cache-type-v", cache_type_v])
            
            # print(f"[DEBUG] Concurrency config: parallel={parallel}, batch_size={batch_size}, ubatch_size={ubatch_size}")
            
            # 如果是推理模型，启用思考模式
            model_type = model_config.get("type", "language-model")
            if model_type == "reasoning-model":
                cmd.extend(["--reasoning-format", "deepseek"])
                # print(f"[DEBUG] Enabling reasoning mode for {model_config.get('id', 'unknown')}")
            
            # 如果是视觉模型，添加 mmproj 参数
            if model_type == "vision-language-model":
                mmproj_path = model_config.get("mmproj")
                if mmproj_path and os.path.exists(mmproj_path):
                    mmproj_rel = to_relative(mmproj_path)
                    cmd.extend(["--mmproj", mmproj_rel])
                else:
                    print(f"[WARNING] Vision model without mmproj: {model_config.get('id', 'unknown')}")
            
            # 打印 llama-server 启动命令（用于调试参数）
            print(f"\n[LLAMA] Starting llama-server:")
            print(f"        {' '.join(cmd)}\n")
            
            # 获取项目根目录作为工作目录 (LLM 目录)
            cwd = project_root
            
            # 启动进程（不等待）
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=cwd,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
            )
            
            # 启动后台任务来读取进程输出
            asyncio.create_task(self._read_process_output())
            
            # 设置 server_url
            self._server_url = f"http://127.0.0.1:{port}"
            
            # 先设置初始状态为 loading
            # print(f"initialize: setting _model_info for {model_config.get('id', 'unknown')}")
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
            # print(f"initialize: _model_info set, status={self._model_info.status}")
            
            # 等待服务器启动（最多等待 300 秒）
            try:
                await self._wait_for_server(300)
                if self._model_info:
                    self._model_info.status = ModelStatus.LOADED
                print(f"initialize: server ready for {model_config.get('id', 'unknown')}")
                return True
            except Exception as e:
                print(f"initialize: server failed to start: {e}")
                if self._process:
                    self._process.terminate()
                    self._process = None
                if self._model_info:
                    self._model_info.status = ModelStatus.ERROR
                return False
    
    async def _read_process_output(self):
        """读取 llama-server 的输出（不打印）"""
        if not self._process:
            return
        
        try:
            # 在一个独立线程中读取输出，避免阻塞
            import threading
            
            def read_stream(stream, name):
                while True:
                    try:
                        line = stream.readline()
                        if not line:
                            break
                        # print(f"[llama-server {name}] {line.decode('utf-8', errors='ignore').rstrip()}")
                    except:
                        break
            
            # 启动线程读取 stdout 和 stderr
            threading.Thread(target=read_stream, args=(self._process.stdout, "stdout"), daemon=True).start()
            threading.Thread(target=read_stream, args=(self._process.stderr, "stderr"), daemon=True).start()
            
        except Exception as e:
            pass  # 静默忽略
    
    async def _wait_and_set_status(self):
        """后台等待服务器启动并更新状态"""
        try:
            # print(f"_wait_and_set_status: waiting for {self._model_info.id if self._model_info else 'unknown'}")
            
            # 等待服务器启动，同时检查进程是否还在运行
            start_time = datetime.now()
            server_ready = False
            
            while (datetime.now() - start_time).seconds < 300:  # 最多等待 300 秒（5分钟）
                # 检查进程是否还在运行
                if self._process and self._process.poll() is not None:
                    # print(f"[ERROR] llama-server process exited with code: {self._process.returncode}")
                    self._process = None
                    if self._model_info:
                        self._model_info.status = ModelStatus.ERROR
                    return
                
                # 尝试检查服务器是否就绪
                try:
                    await self._wait_for_server(10)  # 每次检查 10 秒
                    server_ready = True
                    break
                except TimeoutError:
                    # 超时，继续等待
                    pass
                except Exception as e:
                    # 其他错误，记录但继续等待
                    pass
                
                await asyncio.sleep(1)
            
            if server_ready:
                # 服务器启动成功，只更新状态字段
                # print(f"_wait_and_set_status: server ready, updating status")
                if self._model_info:
                    self._model_info.status = ModelStatus.LOADED
                # print(f"Model {self._model_info.name if self._model_info else 'unknown'} fully loaded and ready")
            else:
                # print(f"Model loading timeout: server did not start within 300 seconds")
                self._process = None
                if self._model_info:
                    self._model_info.status = ModelStatus.ERROR
        except Exception as e:
            # print(f"Error in _wait_and_set_status: {e}")
            import traceback
            traceback.print_exc()
            self._process = None
            if self._model_info:
                self._model_info.status = ModelStatus.ERROR
    
    async def _wait_for_server(self, timeout: int = 300) -> bool:
        """等待服务器启动并加载模型完成"""
        # print(f"_wait_for_server: waiting for {self._server_url} (timeout={timeout}s)")
        start_time = datetime.now()
        server_started = False
        
        while (datetime.now() - start_time).seconds < timeout:
            # 检查进程是否还在运行
            if self._process and self._process.poll() is not None:
                print(f"_wait_for_server: process exited with code {self._process.returncode}")
                raise RuntimeError(f"llama-server process exited with code {self._process.returncode}")
            
            try:
                async with HttpClient.create_client() as client:
                    # 先检查健康端点
                    health_response = await client.get(f"{self._server_url}/health", timeout=2.0)
                    if health_response.status_code == 200:
                        if not server_started:
                            elapsed = (datetime.now() - start_time).seconds
                            # print(f"_wait_for_server: server started after {elapsed}s, waiting for model load...")
                            server_started = True
                        # 服务器已启动，再检查模型是否加载完成
                        # 通过发送一个简单请求来验证
                        try:
                            test_response = await client.post(
                                f"{self._server_url}/v1/chat/completions",
                                json={
                                    "model": "test",
                                    "messages": [{"role": "user", "content": "test"}],
                                    "max_tokens": 1
                                },
                                timeout=5.0
                            )
                            # 如果返回 200 或 4xx 错误（不是 503），说明模型已加载
                            if test_response.status_code != 503:
                                elapsed = (datetime.now() - start_time).seconds
                                # print(f"_wait_for_server: model ready after {elapsed}s")
                                return True
                        except:
                            pass
            except Exception as e:
                pass
            await asyncio.sleep(1)
        
        elapsed = (datetime.now() - start_time).seconds
        # print(f"_wait_for_server: timeout after {elapsed}s")
        raise TimeoutError("Server failed to start within timeout")
    
    async def generate(
        self, 
        prompt: str, 
        config: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        """流式生成"""
        async with HttpClient.create_client() as client:
            payload = {
                "prompt": prompt,
                "temperature": config.get("temperature", 0.7),
                "top_p": config.get("top_p", 0.8),
                "top_k": config.get("top_k", 20),
                "min_p": config.get("min_p"),
                "max_tokens": config.get("max_tokens", 4096),
                "stream": True
            }
            # 只在 min_p 不为 None 时添加
            if payload["min_p"] is None:
                del payload["min_p"]
            
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
        from time import time
        
        # 检查进程是否在运行
        if not self.is_running:
            raise RuntimeError("llama-server process is not running")
        
        start_time = time()
        
        # 构建消息列表（支持多模态和 tool_calls）
        def build_message(msg):
            """构建消息，保留多模态格式和 tool_calls"""
            # msg 可能是 dict 或对象
            if isinstance(msg, dict):
                # 已经是 dict，直接返回（保留 tool_calls 等字段）
                return msg
            else:
                # 是对象，转换
                if isinstance(msg.content, list):
                    return {"role": msg.role, "content": msg.content}
                else:
                    return {"role": msg.role, "content": str(msg.content)}
        
        payload = {
            "messages": [build_message(m) for m in messages],
            "temperature": config.get("temperature", 0.7),
            "top_p": config.get("top_p", 0.8),
            "top_k": config.get("top_k", 20),
            "min_p": config.get("min_p"),
            "max_tokens": config.get("max_tokens", 4096),
            "stream": False
        }
        
        # 只在 min_p 不为 None 时添加
        if payload["min_p"] is None:
            del payload["min_p"]
        
        # 添加 presence_penalty 和 repeat_penalty
        presence_penalty = config.get("presence_penalty")
        if presence_penalty is not None:
            payload["presence_penalty"] = presence_penalty
        
        repeat_penalty = config.get("repeat_penalty")
        if repeat_penalty is not None:
            payload["repeat_penalty"] = repeat_penalty
        
        # 打印实际使用的参数
        print(f"[LLAMA] Request params: temp={payload.get('temperature')}, top_p={payload.get('top_p')}, top_k={payload.get('top_k')}, presence={payload.get('presence_penalty')}, repeat={payload.get('repeat_penalty')}, max_tokens={payload.get('max_tokens')}")
        
        # 支持 tools 参数
        tools = config.get("tools")
        if tools:
            payload["tools"] = tools
            # print(f"[DEBUG] Adding {len(tools)} tools to payload")
        
        tool_choice = config.get("tool_choice")
        if tool_choice:
            payload["tool_choice"] = tool_choice
        
        # 支持 enable_thinking 参数
        enable_thinking = config.get("enable_thinking")
        if enable_thinking is not None:
            payload["chat_template_kwargs"] = {"enable_thinking": enable_thinking}
            # print(f"[DEBUG] chat_template_kwargs: enable_thinking={enable_thinking}")
        
        # 重试逻辑：如果模型正在加载，等待并重试
        max_retries = 10
        retry_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                async with HttpClient.create_client(timeout=300.0) as client:
                    # print(f"llama_backend.chat: sending request to {self._server_url}/v1/chat/completions")
                    response = await client.post(
                        f"{self._server_url}/v1/chat/completions",
                        json=payload
                    )
                    # print(f"llama_backend.chat: response status={response.status_code}, content={response.text[:200]}")
                    result = response.json()
                    
                    # 检查是否是 503 错误（模型加载中）
                    if 'error' in result and result['error'].get('code') == 503:
                        if attempt < max_retries - 1:
                            # print(f"Model loading, retrying in {retry_delay}s... (attempt {attempt + 1}/{max_retries})")
                            await asyncio.sleep(retry_delay)
                            continue
                        else:
                            raise Exception("Model loading timeout. Please try again later.")
                    
                    # print(f"llama-server response: {result}")
                    
                    # 直接透传 llama-server 的响应，保持原始数据结构
                    # 只添加 thinking 字段到 message（如果存在 reasoning_content）
                    if result.get("choices"):
                        message = result["choices"][0].get("message", {})
                        if message.get("reasoning_content"):
                            message["thinking"] = message.pop("reasoning_content")
                    
                    return ChatResponse(
                        id=result.get("id", "chatcmpl-unknown"),
                        created=result.get("created", int(start_time)),
                        model=result.get("model", self._model_info.name if self._model_info else "unknown"),
                        choices=result.get("choices", []),
                        usage=result.get("usage")
                    )
            except Exception as e:
                if attempt < max_retries - 1:
                    # print(f"Request failed, retrying in {retry_delay}s... (attempt {attempt + 1}/{max_retries}): {e}")
                    await asyncio.sleep(retry_delay)
                else:
                    raise e
        
        raise Exception("Failed to get response after all retries")
    
    async def chat_stream(
        self, 
        messages: List[ChatMessage], 
        config: Dict[str, Any]
    ) -> AsyncGenerator[ChatChunk, None]:
        """流式对话 - 直接透传 llama-server 的响应"""
        from time import time
        
        # 检查进程是否在运行
        if not self.is_running:
            raise RuntimeError("llama-server process is not running")
        
        start_time = time()
        
        # 构建消息列表（支持多模态和 tool_calls）
        def build_message(msg):
            """构建消息，保留多模态格式和 tool_calls"""
            if isinstance(msg, dict):
                return msg
            else:
                if isinstance(msg.content, list):
                    return {"role": msg.role, "content": msg.content}
                else:
                    return {"role": msg.role, "content": str(msg.content)}
        
        payload = {
            "messages": [build_message(m) for m in messages],
            "stream": True
        }
        
        # 只传递非 None 的参数，保持与 OpenAI API 一致
        for key in ["temperature", "top_p", "top_k", "min_p", "max_tokens", 
                    "presence_penalty", "frequency_penalty", "repeat_penalty", "stop"]:
            if config.get(key) is not None:
                payload[key] = config[key]
        
        # tools 和 tool_choice
        if config.get("tools"):
            payload["tools"] = config["tools"]
        if config.get("tool_choice"):
            payload["tool_choice"] = config["tool_choice"]
        
        # enable_thinking 参数
        if config.get("enable_thinking") is not None:
            payload["chat_template_kwargs"] = {"enable_thinking": config["enable_thinking"]}
        
        # 直接透传 llama-server 的响应
        async with HttpClient.create_stream_client(timeout=180.0) as client:
            async with client.stream(
                "POST",
                f"{self._server_url}/v1/chat/completions",
                json=payload
            ) as response:
                # 检查响应状态码
                if response.status_code != 200:
                    error_text = await response.aread()
                    print(f"[llama_backend] llama-server returned {response.status_code}: {error_text}")
                    raise RuntimeError(f"llama-server returned {response.status_code}: {error_text.decode('utf-8', errors='ignore')}")
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            # 直接解析并透传 llama-server 的响应（保持原始字段名）
                            chunk_data = json.loads(data)
                            
                            # 调试：打印 llama-server 返回的原始字段
                            delta = chunk_data.get("choices", [{}])[0].get("delta", {})
                            if delta and (delta.get('reasoning_content') or delta.get('content')):
                                pass  # 静默处理
                            
                            yield ChatChunk(
                                id=chunk_data.get("id", "chatcmpl-stream"),
                                created=chunk_data.get("created", int(start_time)),
                                model=chunk_data.get("model", self._model_info.name if self._model_info else "unknown"),
                                choices=chunk_data.get("choices", []),
                                usage=chunk_data.get("usage")
                            )
                        except Exception as e:
                            print(f"[llama_backend] Error parsing chunk: {e}, data: {data[:200]}")
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
