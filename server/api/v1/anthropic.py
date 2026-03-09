"""
Anthropic API 兼容路由
提供 /v1/messages 端点，将请求转换为内部 OpenAI API 调用
"""

import json
import time
import uuid
import logging
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Request, HTTPException, Header
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Optional, List, Any

from server.adapters import AnthropicAdapter, map_anthropic_to_openai_model
from server.core.manager import get_model_manager
from server.services.backend_manager import get_backend_manager
from server.core.backend import ChatMessage

router = APIRouter()

# 创建适配器实例
adapter = AnthropicAdapter()

# 配置日志
log_dir = Path("logs/anthropic")
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / f"messages_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@router.post("/messages")
async def anthropic_messages(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="x-api-key"),
    authorization: Optional[str] = Header(None)
):
    """
    Anthropic Messages API 端点

    兼容 Anthropic Claude API 格式，内部转换为 OpenAI API 调用
    """
    # 生成请求 ID
    request_id = f"req_{uuid.uuid4().hex[:12]}"
    timestamp = datetime.now().isoformat()
    
    # 解析请求体
    try:
        body = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    
    # 记录完整请求到日志
    logger.info(f"\n{'='*80}")
    logger.info(f"[REQUEST {request_id}] {timestamp}")
    logger.info(f"{'='*80}")
    logger.info(f"Method: POST {request.url.path}")
    logger.info(f"Headers: {dict(request.headers)}")
    logger.info(f"Body:\n{json.dumps(body, indent=2, ensure_ascii=False)}")
    logger.info(f"{'='*80}\n")
    
    # 强制打印入口日志
    print(f"\n{'='*60}")
    print(f"[ANTHROPIC] ENTER anthropic_messages | Request ID: {request_id}")
    print(f"{'='*60}")

    # 打印关键请求信息（精简版）
    print(f"\n[ANTHROPIC] {request.method} {request.url.path} | model={body.get('model', 'N/A')} | stream={body.get('stream', False)}")

    # 打印 tools（如果有）
    tools = body.get('tools', [])
    if tools:
        print(f"[ANTHROPIC] Tools: {[t.get('name') for t in tools]}")

    # 打印最后一条消息（用于查看用户输入）
    messages = body.get('messages', [])
    if messages:
        last_msg = messages[-1]
        content = last_msg.get('content', '')
        if isinstance(content, list):
            # 处理多模态内容
            content_str = str(content)[:100]
        else:
            content_str = str(content)[:100]
        print(f"[ANTHROPIC] Last message ({last_msg.get('role')}): {content_str}{'...' if len(str(content)) > 100 else ''}")

    # 打印消息数量
    print(f"[ANTHROPIC] Total messages: {len(messages)}")

    # 验证必要参数
    if "messages" not in body:
        return JSONResponse(
            status_code=400,
            content={
                "type": "error",
                "error": {
                    "type": "invalid_request_error",
                    "message": "messages is required"
                }
            }
        )

    if "max_tokens" not in body:
        return JSONResponse(
            status_code=400,
            content={
                "type": "error",
                "error": {
                    "type": "invalid_request_error",
                    "message": "max_tokens is required"
                }
            }
        )

    # 获取 Anthropic 模型名
    anthropic_model = body.get("model", "claude-3-sonnet-20240229")

    # 检查模型是否存在
    model_manager = get_model_manager()
    backend_manager = get_backend_manager()

    if not model_manager or not backend_manager:
        return JSONResponse(
            status_code=500,
            content={
                "type": "error",
                "error": {
                    "type": "api_error",
                    "message": "Server not initialized"
                }
            }
        )

    openai_model = map_anthropic_to_openai_model(anthropic_model)

    if openai_model not in model_manager.models:
        return JSONResponse(
            status_code=400,
            content={
                "type": "error",
                "error": {
                    "type": "invalid_request_error",
                    "message": f"model '{anthropic_model}' not found"
                }
            }
        )

    # 转换请求为 OpenAI 格式
    try:
        openai_body = adapter.convert_request(body)
        # 打印转换后的 OpenAI 请求（用于调试）
        print(f"[ANTHROPIC] Converted OpenAI request keys: {list(openai_body.keys())}")
        if 'tools' in openai_body:
            print(f"[ANTHROPIC] Tools in OpenAI request: {[t.get('function', {}).get('name') for t in openai_body.get('tools', [])]}")
        # 打印转换后的 messages（用于调试 content type 问题）
        for i, msg in enumerate(openai_body.get('messages', [])):
            content = msg.get('content', '')
            if isinstance(content, list):
                types = []
                for c in content:
                    if isinstance(c, dict):
                        types.append(c.get('type'))
                    else:
                        types.append(type(c).__name__)
                print(f"[ANTHROPIC] Message {i} ({msg.get('role')}): content is list with types: {types}")
            else:
                print(f"[ANTHROPIC] Message {i} ({msg.get('role')}): content is string, len={len(str(content))}")
    except Exception as e:
        import traceback
        print(f"[ANTHROPIC] Error converting request: {e}")
        print(f"[ANTHROPIC] Traceback: {traceback.format_exc()}")
        return JSONResponse(
            status_code=400,
            content={
                "type": "error",
                "error": {
                    "type": "invalid_request_error",
                    "message": str(e)
                }
            }
        )

    # 获取模型配置
    model_config = model_manager.get_model(openai_model)

    # 自动加载模型
    if openai_model not in backend_manager.get_loaded_models():
        print(f"[Anthropic] Model {openai_model} not loaded, auto-loading...")

        # 卸载其他模型
        loaded_models = backend_manager.get_loaded_models()
        if loaded_models:
            for old_model in loaded_models:
                if old_model != openai_model:
                    print(f"[Anthropic] Unloading old model: {old_model}")
                    await backend_manager.unload_model(old_model)
                    model_manager.update_model_status(old_model, "unloaded")

        # 加载模型
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
            "cache_type_v": model_config.cache_type_v,
        }

        success = await backend_manager.load_model(openai_model, model_config.path, model_load_config)
        if success:
            model_manager.update_model_status(openai_model, "loaded")
            print(f"[Anthropic] Model {openai_model} loaded successfully")
        else:
            return JSONResponse(
                status_code=500,
                content={
                    "type": "error",
                    "error": {
                        "type": "api_error",
                        "message": f"Failed to load model {openai_model}"
                    }
                }
            )

    # 构建消息 - 将字典转换为 ChatMessage 对象
    raw_messages = openai_body.get("messages", [])
    messages: List[ChatMessage] = []
    for msg_dict in raw_messages:
        # ChatMessage 是 dataclass，需要正确初始化
        msg = ChatMessage(
            role=msg_dict.get("role", "user"),
            content=msg_dict.get("content", "")
        )
        messages.append(msg)
    
    print(f"[ANTHROPIC] Converted {len(messages)} messages to ChatMessage objects")

    # 构建生成配置
    config = {
        "temperature": openai_body.get("temperature", 0.7),
        "max_tokens": openai_body.get("max_tokens", 1024),
    }

    if "top_p" in openai_body:
        config["top_p"] = openai_body["top_p"]
    if "top_k" in openai_body:
        config["top_k"] = openai_body["top_k"]
    if "stop" in openai_body:
        config["stop"] = openai_body["stop"]

    # 判断是否流式响应
    is_stream = body.get("stream", False)

    if is_stream:
        # 流式响应 - 先检查是否有工具调用，如果有则切换为非流式
        full_content = ""
        tool_use_detected = False
        collected_chunks = []
        
        async for chunk in backend_manager.chat_stream(openai_model, messages, config):
            content = ""
            thinking = ""
            reasoning_content = ""

            if hasattr(chunk, 'choices') and chunk.choices:
                choice = chunk.choices[0]
                if isinstance(choice, dict):
                    delta = choice.get('delta', {})
                    if isinstance(delta, dict):
                        content = delta.get('content', '')
                        thinking = delta.get('thinking', '')
                        reasoning_content = delta.get('reasoning_content', '')
                    else:
                        content = getattr(delta, 'content', '')
                        thinking = getattr(delta, 'thinking', '')
                        reasoning_content = getattr(delta, 'reasoning_content', '')
                else:
                    delta = getattr(choice, 'delta', None)
                    if delta:
                        if isinstance(delta, dict):
                            content = delta.get('content', '')
                            thinking = delta.get('thinking', '')
                            reasoning_content = delta.get('reasoning_content', '')
                        else:
                            content = getattr(delta, 'content', '')
                            thinking = getattr(delta, 'thinking', '')
                            reasoning_content = getattr(delta, 'reasoning_content', '')

            if not content and thinking:
                content = thinking
            if not content and reasoning_content:
                content = reasoning_content

            if content:
                full_content += content
                collected_chunks.append(content)

            # 检查是否是工具调用
            tool_use_patterns = [
                ("<tool_use>", "</tool_use>"),
                ("<tool-use>", "</tool-use>"),
                ("<tool use>", "</tool use>"),
            ]
            for open_tag, close_tag in tool_use_patterns:
                if open_tag in full_content and close_tag in full_content:
                    tool_use_detected = True
                    break
            
            if tool_use_detected:
                break

        # 如果检测到工具调用，返回非流式响应
        if tool_use_detected:
            openai_response = {
                "id": f"chatcmpl-{str(uuid.uuid4())[:10]}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": openai_model,
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": full_content
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": len(full_content) // 4,
                    "total_tokens": len(full_content) // 4
                }
            }
            anthropic_response = adapter.convert_response(openai_response, anthropic_model)
            return JSONResponse(content=anthropic_response)

        # 没有检测到工具调用，继续流式响应（使用已收集的chunks）
        async def resume_stream_generator():
            for chunk_content in collected_chunks:
                yield f"data: {json.dumps({'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'text_delta', 'text': chunk_content}})}\n\n"
            yield f"data: {json.dumps({'type': 'content_block_stop', 'index': 0})}\n\n"
            yield f"data: {json.dumps({'type': 'message_delta', 'delta': {'stop_reason': 'end_turn', 'stop_sequence': None}, 'usage': {'output_tokens': len(full_content) // 4}})}\n\n"
            yield f"data: {json.dumps({'type': 'message_stop'})}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            resume_stream_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
    else:
        # 非流式响应
        try:
            response = await backend_manager.chat(openai_model, messages, config)

            # 从 ChatResponse 对象提取内容
            content = ""
            thinking = ""
            reasoning_content = ""
            if hasattr(response, 'choices') and response.choices:
                choice = response.choices[0]
                if isinstance(choice, dict):
                    message = choice.get('message', {})
                    if isinstance(message, dict):
                        content = message.get('content', '')
                        thinking = message.get('thinking', '')
                        reasoning_content = message.get('reasoning_content', '')
                    else:
                        content = getattr(message, 'content', '')
                        thinking = getattr(message, 'thinking', '')
                        reasoning_content = getattr(message, 'reasoning_content', '')
                else:
                    message = getattr(choice, 'message', {})
                    if isinstance(message, dict):
                        content = message.get('content', '')
                        thinking = message.get('thinking', '')
                        reasoning_content = message.get('reasoning_content', '')
                    else:
                        content = getattr(message, 'content', '')
                        thinking = getattr(message, 'thinking', '')
                        reasoning_content = getattr(message, 'reasoning_content', '')

            # 如果 content 为空但有 thinking 或 reasoning_content，使用它们作为内容
            if not content and thinking:
                content = thinking
            if not content and reasoning_content:
                content = reasoning_content

            # 打印模型返回的原始内容（用于调试工具调用）
            print(f"[ANTHROPIC] Raw content from model: {content[:500]}{'...' if len(content) > 500 else ''}")

            # 获取 usage
            usage = getattr(response, 'usage', {}) or {}
            prompt_tokens = usage.get('prompt_tokens', 0) if isinstance(usage, dict) else getattr(usage, 'prompt_tokens', 0)
            completion_tokens = usage.get('completion_tokens', 0) if isinstance(usage, dict) else getattr(usage, 'completion_tokens', 0)
            total_tokens = usage.get('total_tokens', 0) if isinstance(usage, dict) else getattr(usage, 'total_tokens', 0)

            # 构建 OpenAI 格式的响应
            openai_response = {
                "id": f"chatcmpl-{str(uuid.uuid4())[:10]}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": openai_model,
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": content
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens
                }
            }

            # 转换为 Anthropic 响应格式
            anthropic_response = adapter.convert_response(openai_response, anthropic_model)

            return JSONResponse(content=anthropic_response)

        except Exception as e:
            import traceback
            print(f"[ANTHROPIC ERROR] {type(e).__name__}: {e}")
            print(f"[ANTHROPIC ERROR] Traceback: {traceback.format_exc()}")
            return JSONResponse(
                status_code=500,
                content={
                    "type": "error",
                    "error": {
                        "type": "api_error",
                        "message": str(e)
                    }
                }
            )


async def anthropic_stream_generator(backend_manager, model_id: str, messages: list, config: dict, anthropic_model: str):
    """
    生成 Anthropic 格式的流式响应
    """
    stream_converter = adapter.create_stream_converter(anthropic_model)
    message_id = f"msg_{str(uuid.uuid4())[:12]}"

    try:
        # 发送 message_start 事件
        yield f"event: message_start\ndata: {json.dumps({'type': 'message_start', 'message': {'id': message_id, 'type': 'message', 'role': 'assistant', 'model': anthropic_model, 'content': []}})}\n\n"

        # 发送 content_block_start 事件
        yield f"event: content_block_start\ndata: {json.dumps({'type': 'content_block_start', 'index': 0, 'content_block': {'type': 'text', 'text': ''}})}\n\n"

        # 收集完整内容用于 usage 计算
        full_content = ""

        # 调用后端流式接口
        async for chunk in backend_manager.chat_stream(model_id, messages, config):
            # 处理 ChatChunk 对象
            content = ""
            thinking = ""
            reasoning_content = ""

            if hasattr(chunk, 'choices') and chunk.choices:
                choice = chunk.choices[0]
                if isinstance(choice, dict):
                    delta = choice.get('delta', {})
                    if isinstance(delta, dict):
                        content = delta.get('content', '')
                        thinking = delta.get('thinking', '')
                        reasoning_content = delta.get('reasoning_content', '')
                    else:
                        content = getattr(delta, 'content', '')
                        thinking = getattr(delta, 'thinking', '')
                        reasoning_content = getattr(delta, 'reasoning_content', '')
                else:
                    delta = getattr(choice, 'delta', {})
                    if isinstance(delta, dict):
                        content = delta.get('content', '')
                        thinking = delta.get('thinking', '')
                        reasoning_content = delta.get('reasoning_content', '')
                    else:
                        content = getattr(delta, 'content', '')
                        thinking = getattr(delta, 'thinking', '')
                        reasoning_content = getattr(delta, 'reasoning_content', '')

            # 如果 content 为空但有 thinking 或 reasoning_content，使用它们
            if not content and thinking:
                content = thinking
            if not content and reasoning_content:
                content = reasoning_content

            if content:
                full_content += content
                # 发送 content_block_delta 事件
                yield f"event: content_block_delta\ndata: {json.dumps({'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'text_delta', 'text': content}})}\n\n"

        # 发送 content_block_stop 事件
        yield f"event: content_block_stop\ndata: {json.dumps({'type': 'content_block_stop', 'index': 0})}\n\n"

        # 检测是否有工具调用
        stop_reason = "end_turn"
        # 检查多种可能的工具调用格式（包括空格、下划线、连字符）
        tool_use_patterns = [
            ("<tool_use>", "</tool_use>"),
            ("<tool-use>", "</tool-use>"),
            ("<tool use>", "</tool use>"),
            ("<tool_use>", "</tool-use>"),
            ("<tool-use>", "</tool_use>"),
        ]
        for open_tag, close_tag in tool_use_patterns:
            if open_tag in full_content and close_tag in full_content:
                stop_reason = "tool_use"
                break

        # 发送 message_delta 事件
        yield f"event: message_delta\ndata: {json.dumps({'type': 'message_delta', 'delta': {'stop_reason': stop_reason, 'stop_sequence': None}, 'usage': {'output_tokens': len(full_content) // 4}})}\n\n"

        # 发送 message_stop 事件
        yield f"event: message_stop\ndata: {json.dumps({'type': 'message_stop'})}\n\n"

    except Exception as e:
        # 发送错误事件
        yield f"event: error\ndata: {json.dumps({'type': 'error', 'error': {'type': 'api_error', 'message': str(e)}})}\n\n"


@router.get("/models")
async def anthropic_list_models(
    x_api_key: Optional[str] = Header(None, alias="x-api-key")
):
    """
    列出支持的 Anthropic 模型
    """
    from server.adapters.model_mapping import list_supported_anthropic_models

    models = list_supported_anthropic_models()

    return {
        "data": [
            {
                "id": model_id,
                "object": "model",
                "created": int(time.time()),
                "owned_by": "anthropic"
            }
            for model_id in models
        ],
        "object": "list"
    }
