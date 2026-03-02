from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

router = APIRouter(prefix="/chat", tags=["聊天接口"])


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 0.8
    top_k: Optional[int] = 20
    max_tokens: Optional[int] = 4096
    stream: Optional[bool] = False
    stop: Optional[List[str]] = None


class ChatResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Dict[str, Any]]
    usage: Dict[str, int]


_backend_manager = None


def set_backend_manager(backend_manager):
    global _backend_manager
    _backend_manager = backend_manager


def get_backend_manager():
    return _backend_manager


@router.post("/completions")
async def chat_completions(request: ChatRequest):
    """聊天完成（支持流式和非流式）"""
    print(f"Received chat request: model={request.model}, messages={len(request.messages)}, stream={request.stream}")
    backend_manager = get_backend_manager()
    if not backend_manager:
        print("Backend manager not initialized")
        raise HTTPException(status_code=500, detail="Backend manager not initialized")
    
    # 检查模型是否已完全加载
    if request.model not in backend_manager.get_loaded_models():
        raise HTTPException(status_code=503, detail=f"Model {request.model} is not loaded")
    
    try:
        from ...core.backend import ChatMessage as BackendChatMessage
        import json
        
        # 过滤掉空的 assistant 消息（避免 llama-server 的 prefill 错误）
        filtered_messages = [
            m for m in request.messages 
            if not (m.role == 'assistant' and (not m.content or m.content.strip() == ''))
        ]
        messages = [BackendChatMessage(role=m.role, content=m.content) for m in filtered_messages]
        print(f"Converted messages: {len(messages)} (filtered from {len(request.messages)})")
        
        config = {
            "temperature": request.temperature,
            "top_p": request.top_p,
            "top_k": request.top_k,
            "max_tokens": request.max_tokens
        }
        
        # 流式响应
        if request.stream:
            print(f"Starting stream for model={request.model}")
            
            async def generate():
                try:
                    async for chunk in backend_manager.chat_stream(request.model, messages, config):
                        # 构造 SSE 格式的响应
                        delta = chunk.choices[0].get("delta", {}) if chunk.choices else {}
                        chunk_data = {
                            "id": chunk.id,
                            "object": "chat.completion.chunk",
                            "created": chunk.created,
                            "model": chunk.model,
                            "choices": [{
                                "index": 0,
                                "delta": {
                                    "content": delta.get("content", ""),
                                    "thinking": delta.get("thinking", "")
                                },
                                "finish_reason": chunk.choices[0].get("finish_reason") if chunk.choices else None
                            }]
                        }
                        yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
                    yield "data: [DONE]\n\n"
                except Exception as e:
                    print(f"Stream error: {e}")
                    error_data = {"error": str(e)}
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
        print(f"Calling backend_manager.chat with model={request.model}")
        response = await backend_manager.chat(request.model, messages, config)
        print(f"Got response from backend: {response.id}")
        
        return ChatResponse(
            id=response.id,
            created=response.created,
            model=response.model,
            choices=response.choices,
            usage=response.usage
        )
        
    except Exception as e:
        print(f"Error in chat_completions: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """流式聊天完成"""
    backend_manager = get_backend_manager()
    if not backend_manager:
        raise HTTPException(status_code=500, detail="Backend manager not initialized")
    
    if not request.stream:
        return await chat_completions(request)
    
    try:
        from ...core.backend import ChatMessage as BackendChatMessage
        
        messages = [BackendChatMessage(role=m.role, content=m.content) for m in request.messages]
        
        config = {
            "temperature": request.temperature,
            "top_p": request.top_p,
            "top_k": request.top_k,
            "max_tokens": request.max_tokens
        }
        
        async def generate():
            async for chunk in backend_manager.chat_stream(request.model, messages, config):
                yield f"data: {chunk.json()}\n\n"
            yield "data: [DONE]\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
