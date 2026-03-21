from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse, JSONResponse
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel
import json
import uuid
from time import time

from ...backends.embedding_backend import (
    get_embeddings, initialize_embedding_backend,
    get_embedding_manager
)

# 导入推理监控器
from ...services.inference_monitor import get_inference_monitor

# 导入文件存储和批处理管理
from ...services.file_storage import get_file_storage
from ...services.batch_manager import get_batch_manager

# 导入 Assistant 管理
from ...services.assistant_manager import get_assistant_manager

router = APIRouter(tags=["OpenAI 兼容接口"])

# 初始化 Embedding 后端（延迟初始化）
_embedding_initialized = False

async def ensure_embedding_backend(model_id: str = None):
    """确保 Embedding 后端已初始化
    
    Args:
        model_id: 模型 ID，如果提供则尝试加载对应的 embedding 模型配置
    """
    global _embedding_initialized
    manager = get_embedding_manager()

    if not _embedding_initialized or (model_id and manager.get_config().get("model_id") != model_id):
        config = {
            "type": "local",
            "model": "all-MiniLM-L6-v2",
            "dimension": 384,
            "model_id": model_id
        }

        # 如果提供了模型 ID，尝试加载配置
        if model_id and _model_manager:
            try:
                model_config = _model_manager.get_model(model_id)
                if model_config:
                    # 检查是否是 embedding 模型
                    if model_config.type == "embedding-model":
                        config["format"] = "gguf" if model_config.format == "gguf" else "pytorch"
                        config["model_path"] = model_config.path
                        config["dimension"] = getattr(model_config, 'dimension', 1024)
                        config["max_context"] = model_config.max_context
                        print(f"[Embedding] Loading model from config: {model_id}, format={config['format']}, path={model_config.path}")
                    else:
                        print(f"[Embedding] Model {model_id} is not an embedding model (type={model_config.type})")
            except Exception as e:
                print(f"[Embedding] Failed to load model config for {model_id}: {e}")

        await initialize_embedding_backend(config)
        _embedding_initialized = True


class ImageUrl(BaseModel):
    url: str


class ContentItem(BaseModel):
    type: str
    text: Optional[str] = None
    image_url: Optional[ImageUrl] = None


class ToolCall(BaseModel):
    id: str
    type: str = "function"
    function: Dict[str, Any]


class ChatMessage(BaseModel):
    role: str
    content: Union[str, List[ContentItem], None] = None
    tool_calls: Optional[List[ToolCall]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None


class ChatRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    min_p: Optional[float] = None
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False
    stop: Optional[List[str]] = None
    presence_penalty: Optional[float] = None
    frequency_penalty: Optional[float] = None
    repeat_penalty: Optional[float] = None
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None


class ChatResponse(BaseModel):
    """直接透传 llama-server 的响应"""
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Dict[str, Any]]
    usage: Optional[Dict[str, Any]] = None


class ModelObject(BaseModel):
    id: str
    object: str = "model"
    created: int
    owned_by: str = "local"


class ModelsResponse(BaseModel):
    object: str = "list"
    data: List[ModelObject]


_backend_manager = None
_model_manager = None


def set_managers(backend_mgr, model_mgr):
    global _backend_manager, _model_manager
    _backend_manager = backend_mgr
    _model_manager = model_mgr


@router.get("/models", response_model=ModelsResponse)
async def list_models():
    """OpenAI 兼容的模型列表接口"""
    if not _model_manager:
        raise HTTPException(status_code=500, detail="Model manager not initialized")
    
    models = _model_manager.list_models()
    current_time = int(time())
    
    data = []
    for m in models:
        data.append(ModelObject(
            id=m.id,
            created=current_time,
            owned_by="local"
        ))
    
    return ModelsResponse(data=data)


@router.get("/models/{model_id}")
async def get_model(model_id: str):
    """OpenAI 兼容的模型详情接口"""
    if not _model_manager:
        raise HTTPException(status_code=500, detail="Model manager not initialized")
    
    model = _model_manager.get_model(model_id)
    if not model:
        raise HTTPException(status_code=404, detail=f"Model not found: {model_id}")
    
    return ModelObject(
        id=model.id,
        created=int(time()),
        owned_by="local"
    )


@router.post("/responses")
async def responses(request: ChatRequest):
    """OpenAI Responses API 兼容接口（重定向到 chat/completions）"""
    print(f"[OpenAI] Responses API called, redirecting to chat/completions")
    return await chat_completions(request)


@router.post("/chat/completions")
async def chat_completions(request: ChatRequest):
    """OpenAI 兼容的聊天完成接口"""
    if not _backend_manager:
        raise HTTPException(status_code=500, detail="Backend manager not initialized")
    
    print(f"[OpenAI] Received chat request: model={request.model}, stream={request.stream}, messages_count={len(request.messages)}")
    
    # 打印完整的请求内容用于调试
    import json
    try:
        request_dict = request.model_dump()
        print(f"[DEBUG] Full request: {json.dumps(request_dict, ensure_ascii=False, indent=2)}")
    except Exception as e:
        print(f"[DEBUG] Failed to dump request: {e}")
    
    if not _model_manager:
        raise HTTPException(status_code=500, detail="Model manager not initialized")
    
    model_config = _model_manager.get_model(request.model)
    if not model_config:
        print(f"[OpenAI] Model not found: {request.model}")
        raise HTTPException(status_code=404, detail=f"Model not found: {request.model}")
    
    # 调试信息：打印模型配置
    print(f"[DEBUG] Model config: cache_type_k={model_config.cache_type_k}, cache_type_v={model_config.cache_type_v}")
    
    if request.model not in _backend_manager.get_loaded_models():
        print(f"[OpenAI] Model {request.model} not loaded, auto-loading...")
        
        loaded_models = _backend_manager.get_loaded_models()
        if loaded_models:
            for old_model in loaded_models:
                if old_model != request.model:
                    print(f"[OpenAI] Unloading old model: {old_model}")
                    await _backend_manager.unload_model(old_model)
                    _model_manager.update_model_status(old_model, "unloaded")
        
        model_load_config = {
            "id": model_config.id,
            "name": model_config.name,
            "type": model_config.type,
            "category": model_config.category,
            "backend": model_config.backend,
            "max_context": model_config.max_context,
            "gpu_layers": model_config.gpu_layers,
            "default_temp": model_config.default_temp,
            "default_top_p": model_config.default_top_p,
            "default_top_k": model_config.default_top_k,
            "enable_thinking": model_config.enable_thinking,
            "parallel": model_config.parallel,
            "batch_size": model_config.batch_size,
            "ubatch_size": getattr(model_config, 'ubatch_size', None),
            "tags": model_config.tags,
            "description": model_config.description,
            "cache_type_k": model_config.cache_type_k,
            "cache_type_v": model_config.cache_type_v
        }
        
        if model_config.mmproj:
            model_load_config["mmproj"] = model_config.mmproj
        
        success = await _backend_manager.load_model(
            request.model,
            model_config.path,
            model_load_config
        )
        
        if success:
            _model_manager.update_model_status(request.model, "loaded")
            print(f"[OpenAI] Model {request.model} loaded successfully")
        else:
            raise HTTPException(status_code=500, detail=f"Failed to load model {request.model}")
    
    try:
        from ...core.backend import ChatMessage as BackendChatMessage
        
        def convert_message(m):
            """转换消息为后端格式，保留 tool_calls"""
            msg_dict = {"role": m.role}
            
            # 处理 content
            if m.content is not None:
                if isinstance(m.content, str):
                    msg_dict["content"] = m.content
                elif isinstance(m.content, list):
                    result = []
                    for item in m.content:
                        if item.type == 'text' and item.text:
                            result.append({"type": "text", "text": item.text})
                        elif item.type == 'image_url' and item.image_url:
                            result.append({
                                "type": "image_url",
                                "image_url": {"url": item.image_url.url}
                            })
                    msg_dict["content"] = result
                else:
                    msg_dict["content"] = str(m.content)
            
            # 保留 tool_calls
            if m.tool_calls:
                msg_dict["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": tc.function
                    } for tc in m.tool_calls
                ]
            
            # 保留 tool_call_id
            if m.tool_call_id:
                msg_dict["tool_call_id"] = m.tool_call_id
            
            # 保留 name
            if m.name:
                msg_dict["name"] = m.name
            
            return msg_dict
        
        # 过滤掉空的 assistant 消息（但保留包含 tool_calls 的消息）
        filtered_messages = [
            m for m in request.messages
            if not (
                m.role == 'assistant'
                and (not m.content or (isinstance(m.content, str) and m.content.strip() == ''))
                and not m.tool_calls
            )
        ]
        
        messages = [convert_message(m) for m in filtered_messages]
        
        default_max_tokens = model_config.default_max_tokens if model_config else 131072
        max_tokens = request.max_tokens if request.max_tokens is not None else default_max_tokens
        
        config = {
            "temperature": request.temperature if request.temperature is not None else (model_config.default_temp if model_config else 0.7),
            "top_p": request.top_p if request.top_p is not None else (model_config.default_top_p if model_config else 0.8),
            "top_k": request.top_k if request.top_k is not None else (model_config.default_top_k if model_config else 20),
            "min_p": request.min_p if request.min_p is not None else None,
            "max_tokens": max_tokens,
            "presence_penalty": request.presence_penalty,
            "repeat_penalty": request.repeat_penalty
        }
        
        # 传递 tools 参数
        if request.tools:
            config["tools"] = request.tools
        if request.tool_choice:
            config["tool_choice"] = request.tool_choice
        
        if model_config and model_config.enable_thinking is not None:
            config["enable_thinking"] = model_config.enable_thinking
        
        if request.stream:
            print(f"[OpenAI] Starting stream response for model: {request.model}")

            # 先检查模型是否已加载
            if request.model not in _backend_manager.get_loaded_models():
                print(f"[OpenAI] Model not loaded: {request.model}")
                raise HTTPException(status_code=503, detail=f"Model not loaded: {request.model}")

            # 生成请求 ID 并记录开始
            stream_request_id = str(uuid.uuid4())
            monitor = get_inference_monitor()
            
            # 估算输入 token 数量
            input_text = json.dumps(messages)
            estimated_input_tokens = len(input_text) // 4
            
            await monitor.start_request(stream_request_id, request.model, estimated_input_tokens)

            async def generate():
                chunk_count = 0
                stream_start_time = time()
                output_tokens = 0
                try:
                    print(f"[OpenAI] Calling chat_stream for model: {request.model}")
                    async for chunk in _backend_manager.chat_stream(request.model, messages, config):
                        chunk_count += 1
                        # 调试：打印 chunk.choices
                        if chunk_count <= 10:
                            print(f"[OpenAI] Chunk {chunk_count}: choices type={type(chunk.choices)}, value={chunk.choices}")
                        
                        # 统计输出token（简单估算：每个字符约0.25个token）
                        delta = chunk.choices[0].get("delta", {}) if chunk.choices else {}
                        if delta.get("content"):
                            output_tokens += max(1, len(delta["content"]) // 4)
                        
                        # 直接透传 llama-server 的 chunk 数据
                        chunk_data = {
                            "id": chunk.id,
                            "object": "chat.completion.chunk",
                            "created": chunk.created,
                            "model": chunk.model,
                            "choices": chunk.choices
                        }
                        # 如果有 usage，也透传
                        if chunk.usage:
                            chunk_data["usage"] = chunk.usage
                            # 使用实际的completion_tokens
                            output_tokens = chunk.usage.get("completion_tokens", output_tokens)
                        yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
                    
                    # 记录请求完成
                    await monitor.end_request(stream_request_id, output_tokens, status="completed")
                    stream_duration = time() - stream_start_time
                    print(f"[OpenAI] Stream completed: {chunk_count} chunks sent in {stream_duration:.2f}s")
                    yield "data: [DONE]\n\n"
                except Exception as e:
                    # 记录请求失败
                    await monitor.end_request(stream_request_id, output_tokens, status="failed", error_message=str(e))
                    stream_duration = time() - stream_start_time
                    print(f"[OpenAI] Stream error after {stream_duration:.2f}s: {e}")
                    import traceback
                    traceback.print_exc()
                    
                    # 如果是进程崩溃，尝试重新加载
                    error_msg = str(e)
                    if "process not running" in error_msg or "Model not loaded" in error_msg:
                        print(f"[OpenAI] Process crashed, cleaning up and will reload on next request")
                        # 清理状态，下次请求会自动重新加载
                        error_data = {"error": {"message": "Model process crashed, will reload on next request", "type": "service_unavailable", "code": 503}}
                    else:
                        error_data = {"error": {"message": error_msg, "type": "internal_error"}}
                    yield f"data: {json.dumps(error_data)}\n\n"
            
            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )
        
        # 生成请求ID并记录开始
        request_id = str(uuid.uuid4())
        monitor = get_inference_monitor()
        
        # 估算输入token数量（简单估算：每4个字符约1个token）
        input_text = json.dumps(messages)
        estimated_input_tokens = len(input_text) // 4
        
        await monitor.start_request(request_id, request.model, estimated_input_tokens)
        
        try:
            response = await _backend_manager.chat(request.model, messages, config)
            
            # 获取输出 token 数量
            output_tokens = 0
            if response.usage:
                output_tokens = response.usage.get("completion_tokens", 0)
                if output_tokens == 0:
                    # 如果没有 completion_tokens，尝试从 content 估算
                    if response.choices and len(response.choices) > 0:
                        content = response.choices[0].get("message", {}).get("content", "")
                        output_tokens = len(content) // 4
            else:
                # 从 content 估算
                if response.choices and len(response.choices) > 0:
                    content = response.choices[0].get("message", {}).get("content", "")
                    output_tokens = len(content) // 4
            
            # 记录请求完成
            await monitor.end_request(request_id, output_tokens, status="completed")
            
            # 直接透传 llama-server 的响应，保持原始数据结构
            return ChatResponse(
                id=response.id,
                created=response.created,
                model=response.model,
                choices=response.choices,
                usage=response.usage
            )
        except Exception as e:
            # 记录请求失败
            await monitor.end_request(request_id, 0, status="failed", error_message=str(e))
            
            # 如果是进程崩溃，清理状态
            error_msg = str(e)
            if "process not running" in error_msg or "Model not loaded" in error_msg:
                print(f"[OpenAI] Process crashed, cleaning up and will reload on next request")
            raise
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Completions API (Legacy) ====================

class CompletionRequest(BaseModel):
    model: str
    prompt: Union[str, List[str]]
    suffix: Optional[str] = None
    max_tokens: Optional[int] = 16
    temperature: Optional[float] = 1.0
    top_p: Optional[float] = 1.0
    n: Optional[int] = 1
    stream: Optional[bool] = False
    logprobs: Optional[int] = None
    echo: Optional[bool] = False
    stop: Optional[Union[str, List[str]]] = None
    presence_penalty: Optional[float] = 0.0
    frequency_penalty: Optional[float] = 0.0
    best_of: Optional[int] = 1


class CompletionResponse(BaseModel):
    id: str
    object: str = "text_completion"
    created: int
    model: str
    choices: List[Dict[str, Any]]
    usage: Dict[str, int]


@router.post("/completions")
async def completions(request: CompletionRequest):
    """OpenAI 兼容的文本补全接口（Legacy）"""
    print(f"[OpenAI] Completions API called: model={request.model}, stream={request.stream}")

    # 将 completion 请求转换为 chat 格式
    prompt = request.prompt if isinstance(request.prompt, str) else request.prompt[0]
    messages = [{"role": "user", "content": prompt}]

    config = {
        "temperature": request.temperature,
        "top_p": request.top_p,
        "max_tokens": request.max_tokens,
        "presence_penalty": request.presence_penalty,
        "frequency_penalty": request.frequency_penalty,
    }

    if request.stop:
        config["stop"] = request.stop if isinstance(request.stop, list) else [request.stop]

    try:
        if request.stream:
            async def generate():
                try:
                    text = ""
                    async for chunk in _backend_manager.chat_stream(request.model, messages, config):
                        delta = chunk.choices[0].get("delta", {}) if chunk.choices else {}
                        content = delta.get("content", "")
                        if content:
                            text += content
                            chunk_data = {
                                "id": chunk.id,
                                "object": "text_completion.chunk",
                                "created": chunk.created,
                                "model": chunk.model,
                                "choices": [{
                                    "index": 0,
                                    "text": content,
                                    "logprobs": None,
                                    "finish_reason": None
                                }]
                            }
                            yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"

                    # 发送完成标记
                    final_data = {
                        "id": chunk.id,
                        "object": "text_completion.chunk",
                        "created": chunk.created,
                        "model": chunk.model,
                        "choices": [{
                            "index": 0,
                            "text": "",
                            "logprobs": None,
                            "finish_reason": "stop"
                        }]
                    }
                    yield f"data: {json.dumps(final_data, ensure_ascii=False)}\n\n"
                    yield "data: [DONE]\n\n"
                except Exception as e:
                    print(f"[OpenAI] Completions stream error: {e}")
                    error_data = {"error": {"message": str(e), "type": "internal_error"}}
                    yield f"data: {json.dumps(error_data)}\n\n"

            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )

        # 非流式响应
        response = await _backend_manager.chat(request.model, messages, config)

        # 提取生成的文本
        generated_text = ""
        if response.choices and len(response.choices) > 0:
            generated_text = response.choices[0].get("message", {}).get("content", "")

        return CompletionResponse(
            id=response.id,
            created=response.created,
            model=response.model,
            choices=[{
                "index": 0,
                "text": generated_text,
                "logprobs": None,
                "finish_reason": "stop"
            }],
            usage=response.usage
        )

    except Exception as e:
        print(f"[OpenAI] Completions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Embeddings API ====================

class EmbeddingRequest(BaseModel):
    input: Union[str, List[str]]
    model: str
    encoding_format: Optional[str] = "float"
    dimensions: Optional[int] = None


class EmbeddingObject(BaseModel):
    object: str = "embedding"
    embedding: List[float]
    index: int


class EmbeddingsResponse(BaseModel):
    object: str = "list"
    data: List[EmbeddingObject]
    model: str
    usage: Dict[str, int]


@router.post("/embeddings")
async def embeddings(request: EmbeddingRequest):
    """OpenAI 兼容的 Embeddings 接口"""
    print(f"[OpenAI] Embeddings API called: model={request.model}, inputs={len(request.input) if isinstance(request.input, list) else 1}")

    try:
        # 确保 Embedding 后端已初始化（传入模型 ID）
        await ensure_embedding_backend(request.model)

        # 将输入转换为列表
        inputs = request.input if isinstance(request.input, list) else [request.input]

        # 调用后端生成 embeddings
        embedding_vectors = await get_embeddings(inputs, model=request.model)

        # 构建响应
        embeddings_data = []
        for i, vector in enumerate(embedding_vectors):
            embeddings_data.append(EmbeddingObject(
                embedding=vector,
                index=i
            ))

        # 估算 token 数量（粗略估计：1 token ≈ 0.75 个单词）
        total_tokens = sum(len(text.split()) for text in inputs)

        print(f"[OpenAI] Embeddings generated: {len(embeddings_data)} vectors, dimension={len(embedding_vectors[0]) if embedding_vectors else 0}")

        return EmbeddingsResponse(
            data=embeddings_data,
            model=request.model,
            usage={
                "prompt_tokens": total_tokens,
                "total_tokens": total_tokens
            }
        )

    except Exception as e:
        print(f"[OpenAI] Embeddings error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Audio API ====================

class AudioTranscriptionRequest(BaseModel):
    file: str  # 文件路径或 base64
    model: str
    language: Optional[str] = None
    prompt: Optional[str] = None
    response_format: Optional[str] = "json"
    temperature: Optional[float] = 0.0
    timestamp_granularities: Optional[List[str]] = None


class AudioTranscriptionResponse(BaseModel):
    text: str


@router.post("/audio/transcriptions")
async def audio_transcriptions(request: AudioTranscriptionRequest):
    """OpenAI 兼容的音频转录接口（Whisper）"""
    print(f"[OpenAI] Audio transcription API called: model={request.model}")

    # 当前返回不支持的信息
    raise HTTPException(
        status_code=501,
        detail="Audio transcription is not supported yet. Please use a dedicated Whisper service."
    )


@router.post("/audio/translations")
async def audio_translations(request: AudioTranscriptionRequest):
    """OpenAI 兼容的音频翻译接口（Whisper）"""
    print(f"[OpenAI] Audio translation API called: model={request.model}")

    raise HTTPException(
        status_code=501,
        detail="Audio translation is not supported yet. Please use a dedicated Whisper service."
    )


# ==================== Images API ====================

class ImageGenerationRequest(BaseModel):
    prompt: str
    model: Optional[str] = "dall-e-2"
    n: Optional[int] = 1
    quality: Optional[str] = "standard"
    response_format: Optional[str] = "url"
    size: Optional[str] = "1024x1024"
    style: Optional[str] = None
    user: Optional[str] = None


class ImageGenerationResponse(BaseModel):
    created: int
    data: List[Dict[str, Any]]


@router.post("/images/generations")
async def image_generations(request: ImageGenerationRequest):
    """OpenAI 兼容的图像生成接口（DALL-E）"""
    print(f"[OpenAI] Image generation API called: model={request.model}")

    raise HTTPException(
        status_code=501,
        detail="Image generation is not supported yet. Please use a dedicated image generation service."
    )


# ==================== Files API ====================

class FileObject(BaseModel):
    id: str
    object: str = "file"
    bytes: int
    created_at: int
    filename: str
    purpose: str


class FilesListResponse(BaseModel):
    object: str = "list"
    data: List[FileObject]


@router.get("/files", response_model=FilesListResponse)
async def list_files(purpose: Optional[str] = None):
    """OpenAI 兼容的文件列表接口"""
    print(f"[OpenAI] List files API called, purpose={purpose}")
    
    file_storage = get_file_storage()
    files = file_storage.list_files(purpose=purpose)
    
    return FilesListResponse(data=files)


@router.post("/files")
async def upload_file(
    file: UploadFile = File(...),
    purpose: str = Form(...)
):
    """OpenAI 兼容的文件上传接口"""
    print(f"[OpenAI] Upload file API called: filename={file.filename}, purpose={purpose}")
    
    try:
        # 读取文件内容
        content = await file.read()
        
        # 获取文件类型
        content_type = file.content_type or "application/octet-stream"
        
        # 保存到文件存储
        file_storage = get_file_storage()
        file_obj = file_storage.create_file(
            filename=file.filename,
            purpose=purpose,
            content=content,
            content_type=content_type
        )
        
        print(f"[OpenAI] File uploaded successfully: {file_obj['id']}")
        return JSONResponse(content=file_obj)
    
    except Exception as e:
        print(f"[OpenAI] Failed to upload file: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload file: {str(e)}"
        )


@router.get("/files/{file_id}")
async def get_file(file_id: str):
    """OpenAI 兼容的文件详情接口"""
    print(f"[OpenAI] Get file API called: {file_id}")
    
    file_storage = get_file_storage()
    file_obj = file_storage.get_file(file_id)
    
    if not file_obj:
        raise HTTPException(status_code=404, detail=f"File not found: {file_id}")
    
    return JSONResponse(content=file_obj)


@router.delete("/files/{file_id}")
async def delete_file(file_id: str):
    """OpenAI 兼容的文件删除接口"""
    print(f"[OpenAI] Delete file API called: {file_id}")
    
    file_storage = get_file_storage()
    
    if not file_storage.get_file(file_id):
        raise HTTPException(status_code=404, detail=f"File not found: {file_id}")
    
    success = file_storage.delete_file(file_id)
    
    if success:
        return JSONResponse(content={"deleted": True})
    else:
        raise HTTPException(status_code=500, detail="Failed to delete file")


# ==================== Batch API ====================

class BatchRequest(BaseModel):
    input_file_id: str
    endpoint: str
    completion_window: str
    metadata: Optional[Dict[str, str]] = None


class BatchObject(BaseModel):
    id: str
    object: str = "batch"
    endpoint: str
    errors: Optional[Dict[str, Any]] = None
    input_file_id: str
    completion_window: str
    status: str
    output_file_id: Optional[str] = None
    error_file_id: Optional[str] = None
    created_at: int
    in_progress_at: Optional[int] = None
    expires_at: Optional[int] = None
    finalizing_at: Optional[int] = None
    completed_at: Optional[int] = None
    failed_at: Optional[int] = None
    expired_at: Optional[int] = None
    cancelling_at: Optional[int] = None
    cancelled_at: Optional[int] = None
    request_counts: Optional[Dict[str, int]] = None
    metadata: Optional[Dict[str, str]] = None


@router.post("/batches")
async def create_batch(request: BatchRequest):
    """OpenAI 兼容的 Batch 创建接口"""
    print(f"[OpenAI] Create batch API called: endpoint={request.endpoint}, input_file={request.input_file_id}")
    
    # 验证文件是否存在
    file_storage = get_file_storage()
    file_obj = file_storage.get_file(request.input_file_id)
    
    if not file_obj:
        raise HTTPException(
            status_code=400,
            detail=f"Input file not found: {request.input_file_id}"
        )
    
    # 创建批处理任务
    batch_manager = get_batch_manager()
    batch_obj = batch_manager.create_batch(
        input_file_id=request.input_file_id,
        endpoint=request.endpoint,
        completion_window=request.completion_window,
        metadata=request.metadata
    )
    
    print(f"[OpenAI] Batch created successfully: {batch_obj['id']}")
    return JSONResponse(content=batch_obj)


@router.get("/batches/{batch_id}")
async def get_batch(batch_id: str):
    """OpenAI 兼容的 Batch 详情接口"""
    print(f"[OpenAI] Get batch API called: {batch_id}")
    
    batch_manager = get_batch_manager()
    batch_obj = batch_manager.get_batch(batch_id)
    
    if not batch_obj:
        raise HTTPException(status_code=404, detail=f"Batch not found: {batch_id}")
    
    return JSONResponse(content=batch_obj)


@router.get("/batches")
async def list_batches(limit: int = 20, after: Optional[str] = None):
    """OpenAI 兼容的 Batch 列表接口"""
    print(f"[OpenAI] List batches API called, limit={limit}")
    
    batch_manager = get_batch_manager()
    batches = batch_manager.list_batches(limit=limit, after=after)
    
    return JSONResponse(content={"object": "list", "data": batches})


@router.post("/batches/{batch_id}/cancel")
async def cancel_batch(batch_id: str):
    """OpenAI 兼容的 Batch 取消接口"""
    print(f"[OpenAI] Cancel batch API called: {batch_id}")
    
    batch_manager = get_batch_manager()
    batch_obj = batch_manager.get_batch(batch_id)
    
    if not batch_obj:
        raise HTTPException(status_code=404, detail=f"Batch not found: {batch_id}")
    
    # 取消批处理
    cancelled_batch = batch_manager.cancel_batch(batch_id)
    
    return JSONResponse(content=cancelled_batch)


# ==================== Assistant API ====================

class AssistantRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    model: Optional[str] = None
    instructions: Optional[str] = None
    tools: Optional[List[Dict[str, Any]]] = None
    file_ids: Optional[List[str]] = None
    metadata: Optional[Dict[str, str]] = None


class ThreadRequest(BaseModel):
    messages: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, str]] = None


class MessageRequest(BaseModel):
    role: str
    content: str
    metadata: Optional[Dict[str, str]] = None


class RunRequest(BaseModel):
    assistant_id: str
    instructions: Optional[str] = None
    additional_instructions: Optional[str] = None
    tools: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, str]] = None


@router.post("/assistants")
async def create_assistant(request: AssistantRequest):
    """创建 Assistant"""
    print(f"[OpenAI] Create assistant API called: name={request.name}")
    
    assistant_manager = get_assistant_manager()
    
    assistant = assistant_manager.create_assistant(
        name=request.name or "Assistant",
        model=request.model or "gpt-4",
        description=request.description,
        instructions=request.instructions,
        tools=request.tools,
        metadata=request.metadata
    )
    
    return JSONResponse(content=assistant)


@router.get("/assistants")
async def list_assistants(
    limit: int = 20,
    order: str = "desc",
    after: Optional[str] = None,
    before: Optional[str] = None
):
    """列出 Assistants"""
    print(f"[OpenAI] List assistants API called")
    
    assistant_manager = get_assistant_manager()
    assistants = assistant_manager.list_assistants(
        limit=limit,
        order=order,
        after=after,
        before=before
    )
    
    return JSONResponse(content={"object": "list", "data": assistants})


@router.get("/assistants/{assistant_id}")
async def get_assistant(assistant_id: str):
    """获取 Assistant 详情"""
    print(f"[OpenAI] Get assistant API called: {assistant_id}")
    
    assistant_manager = get_assistant_manager()
    assistant = assistant_manager.get_assistant(assistant_id)
    
    if not assistant:
        raise HTTPException(status_code=404, detail=f"Assistant not found: {assistant_id}")
    
    return JSONResponse(content=assistant)


@router.post("/assistants/{assistant_id}")
async def update_assistant(assistant_id: str, request: AssistantRequest):
    """更新 Assistant"""
    print(f"[OpenAI] Update assistant API called: {assistant_id}")
    
    assistant_manager = get_assistant_manager()
    
    # 构建更新数据
    update_data = {}
    if request.name is not None:
        update_data["name"] = request.name
    if request.model is not None:
        update_data["model"] = request.model
    if request.description is not None:
        update_data["description"] = request.description
    if request.instructions is not None:
        update_data["instructions"] = request.instructions
    if request.tools is not None:
        update_data["tools"] = request.tools
    if request.metadata is not None:
        update_data["metadata"] = request.metadata
    
    assistant = assistant_manager.update_assistant(assistant_id, **update_data)
    
    if not assistant:
        raise HTTPException(status_code=404, detail=f"Assistant not found: {assistant_id}")
    
    return JSONResponse(content=assistant)


@router.delete("/assistants/{assistant_id}")
async def delete_assistant(assistant_id: str):
    """删除 Assistant"""
    print(f"[OpenAI] Delete assistant API called: {assistant_id}")
    
    assistant_manager = get_assistant_manager()
    success = assistant_manager.delete_assistant(assistant_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Assistant not found: {assistant_id}")
    
    return JSONResponse(content={"deleted": True, "id": assistant_id, "object": "assistant.deleted"})


# ==================== Thread API ====================

@router.post("/threads")
async def create_thread(request: ThreadRequest):
    """创建 Thread"""
    print(f"[OpenAI] Create thread API called")
    
    assistant_manager = get_assistant_manager()
    
    thread = assistant_manager.create_thread(
        messages=request.messages,
        metadata=request.metadata
    )
    
    return JSONResponse(content=thread)


@router.get("/threads/{thread_id}")
async def get_thread(thread_id: str):
    """获取 Thread 详情"""
    print(f"[OpenAI] Get thread API called: {thread_id}")
    
    assistant_manager = get_assistant_manager()
    thread = assistant_manager.get_thread(thread_id)
    
    if not thread:
        raise HTTPException(status_code=404, detail=f"Thread not found: {thread_id}")
    
    return JSONResponse(content=thread)


@router.post("/threads/{thread_id}")
async def update_thread(thread_id: str, request: ThreadRequest):
    """更新 Thread"""
    print(f"[OpenAI] Update thread API called: {thread_id}")
    
    assistant_manager = get_assistant_manager()
    thread = assistant_manager.update_thread(
        thread_id=thread_id,
        metadata=request.metadata
    )
    
    if not thread:
        raise HTTPException(status_code=404, detail=f"Thread not found: {thread_id}")
    
    return JSONResponse(content=thread)


@router.delete("/threads/{thread_id}")
async def delete_thread(thread_id: str):
    """删除 Thread"""
    print(f"[OpenAI] Delete thread API called: {thread_id}")
    
    assistant_manager = get_assistant_manager()
    success = assistant_manager.delete_thread(thread_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Thread not found: {thread_id}")
    
    return JSONResponse(content={"deleted": True, "id": thread_id, "object": "thread.deleted"})


# ==================== Message API ====================

@router.post("/threads/{thread_id}/messages")
async def create_message(thread_id: str, request: MessageRequest):
    """创建 Message"""
    print(f"[OpenAI] Create message API called: thread={thread_id}")
    
    assistant_manager = get_assistant_manager()
    
    # 验证线程是否存在
    thread = assistant_manager.get_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail=f"Thread not found: {thread_id}")
    
    message = assistant_manager.add_message(
        thread_id=thread_id,
        role=request.role,
        content=request.content,
        metadata=request.metadata
    )
    
    return JSONResponse(content=message)


@router.get("/threads/{thread_id}/messages")
async def list_messages(
    thread_id: str,
    limit: int = 20,
    order: str = "desc"
):
    """列出 Messages"""
    print(f"[OpenAI] List messages API called: thread={thread_id}")
    
    assistant_manager = get_assistant_manager()
    
    # 验证线程是否存在
    thread = assistant_manager.get_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail=f"Thread not found: {thread_id}")
    
    messages = assistant_manager.list_messages(
        thread_id=thread_id,
        limit=limit,
        order=order
    )
    
    return JSONResponse(content={"object": "list", "data": messages})


@router.get("/threads/{thread_id}/messages/{message_id}")
async def get_message(thread_id: str, message_id: str):
    """获取 Message 详情"""
    print(f"[OpenAI] Get message API called: thread={thread_id}, message={message_id}")
    
    assistant_manager = get_assistant_manager()
    message = assistant_manager.get_message(thread_id, message_id)
    
    if not message:
        raise HTTPException(status_code=404, detail=f"Message not found: {message_id}")
    
    return JSONResponse(content=message)


# ==================== Run API ====================

@router.post("/threads/{thread_id}/runs")
async def create_run(thread_id: str, request: RunRequest):
    """创建 Run"""
    print(f"[OpenAI] Create run API called: thread={thread_id}")
    
    assistant_manager = get_assistant_manager()
    
    # 验证线程是否存在
    thread = assistant_manager.get_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail=f"Thread not found: {thread_id}")
    
    run = assistant_manager.create_run(
        thread_id=thread_id,
        assistant_id=request.assistant_id,
        instructions=request.instructions,
        additional_instructions=request.additional_instructions,
        tools=request.tools,
        metadata=request.metadata
    )
    
    return JSONResponse(content=run)


@router.get("/threads/{thread_id}/runs")
async def list_runs(
    thread_id: str,
    limit: int = 20
):
    """列出 Runs"""
    print(f"[OpenAI] List runs API called: thread={thread_id}")
    
    assistant_manager = get_assistant_manager()
    
    # 验证线程是否存在
    thread = assistant_manager.get_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail=f"Thread not found: {thread_id}")
    
    runs = assistant_manager.list_runs(
        thread_id=thread_id,
        limit=limit
    )
    
    return JSONResponse(content={"object": "list", "data": runs})


@router.get("/threads/{thread_id}/runs/{run_id}")
async def get_run(thread_id: str, run_id: str):
    """获取 Run 详情"""
    print(f"[OpenAI] Get run API called: thread={thread_id}, run={run_id}")
    
    assistant_manager = get_assistant_manager()
    run = assistant_manager.get_run(run_id)
    
    if not run or run.get("thread_id") != thread_id:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    
    return JSONResponse(content=run)


@router.post("/threads/{thread_id}/runs/{run_id}/cancel")
async def cancel_run(thread_id: str, run_id: str):
    """取消 Run"""
    print(f"[OpenAI] Cancel run API called: thread={thread_id}, run={run_id}")
    
    assistant_manager = get_assistant_manager()
    run = assistant_manager.get_run(run_id)
    
    if not run or run.get("thread_id") != thread_id:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    
    cancelled_run = assistant_manager.cancel_run(run_id)
    
    return JSONResponse(content=cancelled_run)
