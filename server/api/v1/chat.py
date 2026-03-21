from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel
import uuid

router = APIRouter(prefix="/chat", tags=["聊天接口"])

# 导入推理监控器
from ...services.inference_monitor import get_inference_monitor


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
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 0.8
    top_k: Optional[int] = 20
    min_p: Optional[float] = None
    max_tokens: Optional[int] = 131072
    stream: Optional[bool] = False
    stop: Optional[List[str]] = None
    presence_penalty: Optional[float] = None
    frequency_penalty: Optional[float] = None
    repeat_penalty: Optional[float] = None
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None


class ChatResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Dict[str, Any]]
    usage: Optional[Dict[str, int]] = None


_backend_manager = None
_model_manager = None


def set_backend_manager(backend_manager):
    global _backend_manager
    _backend_manager = backend_manager


def set_model_manager(model_manager):
    global _model_manager
    _model_manager = model_manager


def get_backend_manager():
    return _backend_manager


def get_model_manager():
    return _model_manager


@router.post("/completions")
async def chat_completions(request: ChatRequest):
    """聊天完成（支持流式和非流式）"""
    print(f"Received chat request: model={request.model}, messages={len(request.messages)}, stream={request.stream}")
    backend_manager = get_backend_manager()
    model_manager = get_model_manager()
    if not backend_manager:
        print("Backend manager not initialized")
        raise HTTPException(status_code=500, detail="Backend manager not initialized")
    
    # 检查模型是否已完全加载
    if request.model not in backend_manager.get_loaded_models():
        raise HTTPException(status_code=503, detail=f"Model {request.model} is not loaded")
    
    # 获取模型配置中的默认值
    model_config = model_manager.get_model(request.model) if model_manager else None
    default_max_tokens = model_config.default_max_tokens if model_config else 4096
    
    try:
        from ...core.backend import ChatMessage as BackendChatMessage
        import json
        
        # 过滤掉空的 assistant 消息（但保留包含 tool_calls 的消息）
        filtered_messages = [
            m for m in request.messages 
            if not (
                m.role == 'assistant' 
                and (not m.content or (isinstance(m.content, str) and m.content.strip() == ''))
                and not m.tool_calls  # 保留包含 tool_calls 的消息
            )
        ]
        
        # 转换消息格式（保留多模态格式和 tool_calls）
        def convert_message(m):
            """转换消息为后端格式，保留多模态结构和 tool_calls"""
            msg_dict = {"role": m.role}
            
            # 处理 content
            if m.content is not None:
                if isinstance(m.content, str):
                    msg_dict["content"] = m.content
                elif isinstance(m.content, list):
                    # 多模态格式：转换为字典列表
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
            
            # 保留 tool_call_id（用于 tool 角色的消息）
            if m.tool_call_id:
                msg_dict["tool_call_id"] = m.tool_call_id
            
            # 保留 name（用于 function 角色的消息）
            if m.name:
                msg_dict["name"] = m.name
            
            return msg_dict
        
        messages = [convert_message(m) for m in filtered_messages]
        print(f"Converted messages: {len(messages)} (filtered from {len(request.messages)})")
        
        # 使用请求中的值或模型配置中的默认值
        # temperature: 优先使用请求值，否则使用模型配置的 default_temp
        temperature = request.temperature if request.temperature != 0.7 else (model_config.default_temp if model_config else 0.7)
        # top_p: 优先使用请求值，否则使用模型配置的 default_top_p
        top_p = request.top_p if request.top_p != 0.8 else (model_config.default_top_p if model_config else 0.8)
        # top_k: 优先使用请求值，否则使用模型配置的 default_top_k
        top_k = request.top_k if request.top_k != 20 else (model_config.default_top_k if model_config else 20)
        # min_p: 优先使用请求值，否则使用模型配置的 min_p
        min_p = request.min_p if request.min_p is not None else (model_config.min_p if model_config else None)
        # max_tokens: 优先使用请求值（如果不是默认值131072），否则使用模型配置的 default_max_tokens
        max_tokens = request.max_tokens if request.max_tokens != 131072 else default_max_tokens
        # repeat_penalty: 优先使用请求值，否则使用模型配置的 repeat_penalty
        repeat_penalty = request.repeat_penalty if request.repeat_penalty is not None else (model_config.repeat_penalty if model_config else None)
        
        print(f"Using temperature={temperature}, top_p={top_p}, top_k={top_k}, min_p={min_p}, max_tokens={max_tokens}, repeat_penalty={repeat_penalty}")
        
        config = {
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
            "min_p": min_p,
            "max_tokens": max_tokens,
            "presence_penalty": request.presence_penalty,
            "frequency_penalty": request.frequency_penalty,
            "repeat_penalty": repeat_penalty
        }

        # 传递 tools 参数
        if request.tools:
            config["tools"] = request.tools
            print(f"Using tools: {len(request.tools)} tools")
        if request.tool_choice:
            config["tool_choice"] = request.tool_choice
        
        # 传递 enable_thinking 参数
        if model_config and model_config.enable_thinking is not None:
            config["enable_thinking"] = model_config.enable_thinking
            print(f"Using enable_thinking={model_config.enable_thinking}")
        
        # 流式响应
        if request.stream:
            print(f"Starting stream for model={request.model}")
            
            # 生成请求ID并记录开始
            stream_request_id = str(uuid.uuid4())
            monitor = get_inference_monitor()
            
            # 估算输入token数量
            input_text = json.dumps(messages)
            estimated_input_tokens = len(input_text) // 4
            
            await monitor.start_request(stream_request_id, request.model, estimated_input_tokens)
            
            async def generate():
                output_tokens = 0
                try:
                    async for chunk in backend_manager.chat_stream(request.model, messages, config):
                        delta = chunk.choices[0].get("delta", {}) if chunk.choices else {}
                        
                        # 统计输出token（简单估算：每个字符约0.25个token）
                        if delta.get("content"):
                            output_tokens += max(1, len(delta["content"]) // 4)
                        
                        chunk_data = {
                            "id": chunk.id,
                            "object": "chat.completion.chunk",
                            "created": chunk.created,
                            "model": chunk.model,
                            "choices": [{
                                "index": 0,
                                "delta": delta,
                                "finish_reason": chunk.choices[0].get("finish_reason") if chunk.choices else None
                            }]
                        }
                        
                        if chunk.usage and chunk.usage.get("total_tokens", 0) > 0:
                            chunk_data["usage"] = chunk.usage
                            # 使用实际的completion_tokens
                            output_tokens = chunk.usage.get("completion_tokens", output_tokens)
                        
                        yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
                    
                    # 记录请求完成
                    await monitor.end_request(stream_request_id, output_tokens, status="completed")
                    yield "data: [DONE]\n\n"
                except Exception as e:
                    print(f"Stream error: {e}")
                    # 记录请求失败
                    await monitor.end_request(stream_request_id, output_tokens, status="failed", error_message=str(e))
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
        
        # 生成请求ID并记录开始
        request_id = str(uuid.uuid4())
        monitor = get_inference_monitor()
        
        # 估算输入token数量（简单估算：每4个字符约1个token）
        input_text = json.dumps(messages)
        estimated_input_tokens = len(input_text) // 4
        
        await monitor.start_request(request_id, request.model, estimated_input_tokens)
        
        try:
            response = await backend_manager.chat(request.model, messages, config)
            print(f"Got response from backend: {response.id}")
            
            # 获取输出token数量
            output_tokens = 0
            if response.usage:
                output_tokens = response.usage.get("completion_tokens", 0)
                if output_tokens == 0:
                    # 如果没有completion_tokens，尝试从content估算
                    if response.choices and len(response.choices) > 0:
                        content = response.choices[0].get("message", {}).get("content", "")
                        output_tokens = len(content) // 4
            else:
                # 从content估算
                if response.choices and len(response.choices) > 0:
                    content = response.choices[0].get("message", {}).get("content", "")
                    output_tokens = len(content) // 4
            
            # 记录请求完成
            await monitor.end_request(request_id, output_tokens, status="completed")
            
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
            raise
        
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
        # 转换消息格式（保留 tool_calls）
        def convert_message(m):
            msg_dict = {"role": m.role}
            if m.content is not None:
                if isinstance(m.content, str):
                    msg_dict["content"] = m.content
                elif isinstance(m.content, list):
                    result = []
                    for item in m.content:
                        if item.type == 'text' and item.text:
                            result.append({"type": "text", "text": item.text})
                        elif item.type == 'image_url' and item.image_url:
                            result.append({"type": "image_url", "image_url": {"url": item.image_url.url}})
                    msg_dict["content"] = result
                else:
                    msg_dict["content"] = str(m.content)
            if m.tool_calls:
                msg_dict["tool_calls"] = [{"id": tc.id, "type": tc.type, "function": tc.function} for tc in m.tool_calls]
            if m.tool_call_id:
                msg_dict["tool_call_id"] = m.tool_call_id
            if m.name:
                msg_dict["name"] = m.name
            return msg_dict
        
        messages = [convert_message(m) for m in request.messages]
        
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
