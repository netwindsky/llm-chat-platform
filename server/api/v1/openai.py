from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel
import json
from time import time

from ...backends.embedding_backend import (
    get_embeddings, initialize_embedding_backend,
    get_embedding_manager
)

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
            "max_tokens": max_tokens
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

            async def generate():
                chunk_count = 0
                stream_start_time = time()
                try:
                    print(f"[OpenAI] Calling chat_stream for model: {request.model}")
                    async for chunk in _backend_manager.chat_stream(request.model, messages, config):
                        chunk_count += 1
                        delta = chunk.choices[0].get("delta", {}) if chunk.choices else {}
                        delta_dict = {
                            "content": delta.get("content", ""),
                            "thinking": delta.get("thinking", "")
                        }

                        # 保留 tool_calls（如果存在）
                        if "tool_calls" in delta:
                            delta_dict["tool_calls"] = delta["tool_calls"]

                        chunk_data = {
                            "id": chunk.id,
                            "object": "chat.completion.chunk",
                            "created": chunk.created,
                            "model": chunk.model,
                            "choices": [{
                                "index": 0,
                                "delta": delta_dict,
                                "finish_reason": chunk.choices[0].get("finish_reason") if chunk.choices else None
                            }]
                        }
                        yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
                    stream_duration = time() - stream_start_time
                    print(f"[OpenAI] Stream completed: {chunk_count} chunks sent in {stream_duration:.2f}s")
                    yield "data: [DONE]\n\n"
                except Exception as e:
                    stream_duration = time() - stream_start_time
                    print(f"[OpenAI] Stream error after {stream_duration:.2f}s: {e}")
                    import traceback
                    traceback.print_exc()
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
        
        response = await _backend_manager.chat(request.model, messages, config)
        
        # 直接透传 llama-server 的响应，保持原始数据结构
        return ChatResponse(
            id=response.id,
            created=response.created,
            model=response.model,
            choices=response.choices,
            usage=response.usage
        )
        
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

    # 返回空列表
    return FilesListResponse(data=[])


@router.post("/files")
async def upload_file():
    """OpenAI 兼容的文件上传接口"""
    print(f"[OpenAI] Upload file API called")

    raise HTTPException(
        status_code=501,
        detail="File upload is not supported yet."
    )


@router.get("/files/{file_id}")
async def get_file(file_id: str):
    """OpenAI 兼容的文件详情接口"""
    print(f"[OpenAI] Get file API called: {file_id}")

    raise HTTPException(status_code=404, detail=f"File not found: {file_id}")


@router.delete("/files/{file_id}")
async def delete_file(file_id: str):
    """OpenAI 兼容的文件删除接口"""
    print(f"[OpenAI] Delete file API called: {file_id}")

    raise HTTPException(status_code=404, detail=f"File not found: {file_id}")


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
    print(f"[OpenAI] Create batch API called: endpoint={request.endpoint}")

    raise HTTPException(
        status_code=501,
        detail="Batch API is not supported yet."
    )


@router.get("/batches/{batch_id}")
async def get_batch(batch_id: str):
    """OpenAI 兼容的 Batch 详情接口"""
    print(f"[OpenAI] Get batch API called: {batch_id}")

    raise HTTPException(status_code=404, detail=f"Batch not found: {batch_id}")


@router.get("/batches")
async def list_batches(limit: int = 20, after: Optional[str] = None):
    """OpenAI 兼容的 Batch 列表接口"""
    print(f"[OpenAI] List batches API called")

    return {"object": "list", "data": []}


@router.post("/batches/{batch_id}/cancel")
async def cancel_batch(batch_id: str):
    """OpenAI 兼容的 Batch 取消接口"""
    print(f"[OpenAI] Cancel batch API called: {batch_id}")

    raise HTTPException(status_code=404, detail=f"Batch not found: {batch_id}")
