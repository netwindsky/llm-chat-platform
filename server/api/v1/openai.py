from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel
import json
from time import time

router = APIRouter(tags=["OpenAI 兼容接口"])


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
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False
    stop: Optional[List[str]] = None
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None


class ChatResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Dict[str, Any]]
    usage: Dict[str, int]


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


@router.post("/chat/completions")
async def chat_completions(request: ChatRequest):
    """OpenAI 兼容的聊天完成接口"""
    if not _backend_manager:
        raise HTTPException(status_code=500, detail="Backend manager not initialized")
    
    if not _model_manager:
        raise HTTPException(status_code=500, detail="Model manager not initialized")
    
    model_config = _model_manager.get_model(request.model)
    if not model_config:
        raise HTTPException(status_code=404, detail=f"Model not found: {request.model}")
    
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
            "max_context": model_config.max_context,
            "gpu_layers": 99,
            "default_temp": model_config.default_temp,
            "default_top_p": model_config.default_top_p,
            "default_top_k": model_config.default_top_k,
            "enable_thinking": model_config.enable_thinking,
            "parallel": model_config.parallel,
            "batch_size": model_config.batch_size,
            "tags": model_config.tags,
            "description": model_config.description
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
        
        default_max_tokens = model_config.default_max_tokens if model_config else 4096
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
            async def generate():
                try:
                    async for chunk in _backend_manager.chat_stream(request.model, messages, config):
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
                    yield "data: [DONE]\n\n"
                except Exception as e:
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
        
        return ChatResponse(
            id=response.id,
            created=response.created,
            model=response.model,
            choices=response.choices,
            usage=response.usage
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
