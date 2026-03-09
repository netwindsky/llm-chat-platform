# OpenAI API 转换 Anthropic API 适配方案

## 概述

在不改变原有 OpenAI 接口的情况下，添加 Anthropic 代理接口支持。通过适配器层将 Anthropic API 请求转换为 OpenAI API 请求，并将 OpenAI 响应转换为 Anthropic 响应格式。

## API 格式差异对比

### 1. 请求格式差异

#### OpenAI Chat Completions API
```json
POST /v1/chat/completions
{
  "model": "gpt-4",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"}
  ],
  "temperature": 0.7,
  "max_tokens": 1024,
  "stream": false
}
```

#### Anthropic Messages API
```json
POST /v1/messages
{
  "model": "claude-3-sonnet-20240229",
  "max_tokens": 1024,
  "messages": [
    {"role": "user", "content": "Hello!"}
  ],
  "system": "You are a helpful assistant.",
  "temperature": 0.7,
  "stream": false
}
```

**关键差异：**
- 端点不同：`/v1/chat/completions` vs `/v1/messages`
- 消息格式：OpenAI 使用 `messages` 包含 system，Anthropic 使用独立的 `system` 字段
- 角色定义：OpenAI 有 `system/user/assistant/tool`，Anthropic 有 `user/assistant`

### 2. 响应格式差异

#### OpenAI 响应
```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "gpt-4",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "Hello! How can I help you today?"
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 20,
    "completion_tokens": 10,
    "total_tokens": 30
  }
}
```

#### Anthropic 响应
```json
{
  "id": "msg_01Xxx",
  "type": "message",
  "role": "assistant",
  "model": "claude-3-sonnet-20240229",
  "content": [
    {
      "type": "text",
      "text": "Hello! How can I help you today?"
    }
  ],
  "stop_reason": "end_turn",
  "stop_sequence": null,
  "usage": {
    "input_tokens": 20,
    "output_tokens": 10
  }
}
```

**关键差异：**
- `content` 格式：OpenAI 是字符串，Anthropic 是数组对象
- Token 字段名：OpenAI 使用 `prompt_tokens/completion_tokens`，Anthropic 使用 `input_tokens/output_tokens`
- Finish reason 字段名和值不同

### 3. 流式响应差异

#### OpenAI Stream
```
data: {"id":"chatcmpl-xxx","choices":[{"delta":{"content":"Hello"}}]}

data: {"id":"chatcmpl-xxx","choices":[{"delta":{"content":"!"}}]}

data: [DONE]
```

#### Anthropic Stream
```
event: message_start
data: {"type":"message_start","message":{"id":"msg_xxx"}}

event: content_block_start
data: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}

event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hello"}}

event: content_block_stop
data: {"type":"content_block_stop","index":0}

event: message_stop
data: {"type":"message_stop"}
```

**关键差异：**
- Anthropic 使用 SSE event 类型区分不同事件
- 内容增量格式不同
- 结束标记不同

## 转换方案设计

### 架构图

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Anthropic      │────▶│  Anthropic       │────▶│  OpenAI         │
│  Client         │     │  Adapter         │     │  Backend        │
│                 │◀────│                  │◀────│                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌──────────────────┐
                        │  Model Mapping   │
                        │  (claude-3 ▶     │
                        │   qwen3.5-27b)   │
                        └──────────────────┘
```

### 核心组件

#### 1. 请求转换器 (Request Converter)

```python
class AnthropicRequestConverter:
    """将 Anthropic 请求转换为 OpenAI 请求"""
    
    @staticmethod
    def convert_messages(anthropic_messages: list, system: str = None) -> list:
        """转换消息格式"""
        openai_messages = []
        
        # 添加 system message
        if system:
            openai_messages.append({
                "role": "system",
                "content": system
            })
        
        # 转换 user/assistant messages
        for msg in anthropic_messages:
            openai_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        return openai_messages
    
    @staticmethod
    def convert_request(anthropic_body: dict) -> dict:
        """转换完整请求体"""
        openai_body = {
            "model": map_anthropic_to_openai_model(anthropic_body["model"]),
            "messages": AnthropicRequestConverter.convert_messages(
                anthropic_body["messages"],
                anthropic_body.get("system")
            ),
            "max_tokens": anthropic_body.get("max_tokens", 1024),
            "temperature": anthropic_body.get("temperature", 0.7),
            "stream": anthropic_body.get("stream", False)
        }
        
        # 可选参数
        if "top_p" in anthropic_body:
            openai_body["top_p"] = anthropic_body["top_p"]
        if "stop_sequences" in anthropic_body:
            openai_body["stop"] = anthropic_body["stop_sequences"]
        
        return openai_body
```

#### 2. 响应转换器 (Response Converter)

```python
class AnthropicResponseConverter:
    """将 OpenAI 响应转换为 Anthropic 响应"""
    
    @staticmethod
    def convert_completion(openai_response: dict, anthropic_model: str) -> dict:
        """转换非流式响应"""
        choice = openai_response["choices"][0]
        
        return {
            "id": f"msg_{openai_response['id'][-10:]}",
            "type": "message",
            "role": "assistant",
            "model": anthropic_model,
            "content": [{
                "type": "text",
                "text": choice["message"]["content"]
            }],
            "stop_reason": AnthropicResponseConverter.map_finish_reason(
                choice.get("finish_reason")
            ),
            "stop_sequence": None,
            "usage": {
                "input_tokens": openai_response["usage"]["prompt_tokens"],
                "output_tokens": openai_response["usage"]["completion_tokens"]
            }
        }
    
    @staticmethod
    def map_finish_reason(openai_reason: str) -> str:
        """映射 finish reason"""
        mapping = {
            "stop": "end_turn",
            "length": "max_tokens",
            "content_filter": "content_filter",
            "tool_calls": "tool_use"
        }
        return mapping.get(openai_reason, "end_turn")
```

#### 3. 流式响应转换器

```python
class AnthropicStreamConverter:
    """转换流式响应"""
    
    @staticmethod
    def convert_stream_chunk(openai_chunk: dict, anthropic_model: str) -> list:
        """将 OpenAI 流式块转换为 Anthropic 事件"""
        events = []
        
        # 第一个块：message_start
        if openai_chunk.get("choices") and openai_chunk["choices"][0].get("delta", {}).get("role"):
            events.append({
                "event": "message_start",
                "data": json.dumps({
                    "type": "message_start",
                    "message": {
                        "id": f"msg_{openai_chunk['id'][-10:]}",
                        "type": "message",
                        "role": "assistant",
                        "model": anthropic_model,
                        "content": []
                    }
                })
            })
            events.append({
                "event": "content_block_start",
                "data": json.dumps({
                    "type": "content_block_start",
                    "index": 0,
                    "content_block": {"type": "text", "text": ""}
                })
            })
        
        # 内容增量
        delta = openai_chunk.get("choices", [{}])[0].get("delta", {})
        if delta.get("content"):
            events.append({
                "event": "content_block_delta",
                "data": json.dumps({
                    "type": "content_block_delta",
                    "index": 0,
                    "delta": {"type": "text_delta", "text": delta["content"]}
                })
            })
        
        # 结束块
        finish_reason = openai_chunk.get("choices", [{}])[0].get("finish_reason")
        if finish_reason:
            events.append({
                "event": "content_block_stop",
                "data": json.dumps({"type": "content_block_stop", "index": 0})
            })
            events.append({
                "event": "message_stop",
                "data": json.dumps({"type": "message_stop"})
            })
        
        return events
```

#### 4. 模型映射

```python
# Anthropic 模型名到本地模型名的映射
ANTHROPIC_TO_OPENAI_MODEL_MAP = {
    "claude-3-opus-20240229": "qwen3.5-35b-a3b-ud-q4-xl",
    "claude-3-sonnet-20240229": "qwen3.5-27b-ud-q4-xl-1",
    "claude-3-haiku-20240307": "qwen3.5-9b-ud-q4",
    "claude-3-5-sonnet-20240620": "qwen3.5-27b-ud-q4-xl-1-thinking-general",
    "claude-3-5-sonnet-20241022": "qwen3.5-27b-ud-q4-xl-1-thinking-coding",
}

def map_anthropic_to_openai_model(anthropic_model: str) -> str:
    """将 Anthropic 模型名映射到本地模型名"""
    return ANTHROPIC_TO_OPENAI_MODEL_MAP.get(anthropic_model, "qwen3.5-27b-ud-q4-xl-1")
```

## 路由设计

### Anthropic API 路由

```python
from fastapi import APIRouter, Request, Response
from fastapi.responses import StreamingResponse
import json

router = APIRouter(prefix="/v1")

@router.post("/messages")
async def anthropic_messages(request: Request):
    """Anthropic Messages API 端点"""
    body = await request.json()
    
    # 转换请求
    converter = AnthropicRequestConverter()
    openai_body = converter.convert_request(body)
    
    # 调用内部 OpenAI API
    from server.api.v1.openai import chat_completions
    
    # 创建模拟请求
    class MockRequest:
        def __init__(self, body):
            self._body = body
        async def json(self):
            return self._body
    
    mock_request = MockRequest(openai_body)
    
    # 获取 Anthropic 模型名（用于响应转换）
    anthropic_model = body.get("model", "claude-3-sonnet-20240229")
    
    if body.get("stream", False):
        # 流式响应
        return StreamingResponse(
            anthropic_stream_generator(mock_request, anthropic_model),
            media_type="text/event-stream"
        )
    else:
        # 非流式响应
        openai_response = await chat_completions(mock_request)
        
        # 转换响应
        response_converter = AnthropicResponseConverter()
        anthropic_response = response_converter.convert_completion(
            openai_response,
            anthropic_model
        )
        
        return Response(
            content=json.dumps(anthropic_response),
            media_type="application/json"
        )

async def anthropic_stream_generator(request, anthropic_model: str):
    """生成 Anthropic 格式的流式响应"""
    from server.api.v1.openai import chat_completions
    
    openai_stream = await chat_completions(request)
    converter = AnthropicStreamConverter()
    
    async for chunk in openai_stream.body_iterator:
        if chunk.startswith("data: "):
            data = chunk[6:]
            if data == "[DONE]":
                break
            
            openai_chunk = json.loads(data)
            events = converter.convert_stream_chunk(openai_chunk, anthropic_model)
            
            for event in events:
                yield f"event: {event['event']}\ndata: {event['data']}\n\n"
```

## 实现步骤

### 步骤 1: 创建适配器模块

```
server/
  adapters/
    __init__.py
    anthropic_adapter.py      # 主适配器
    request_converter.py        # 请求转换
    response_converter.py       # 响应转换
    stream_converter.py         # 流式转换
    model_mapping.py            # 模型映射
```

### 步骤 2: 注册路由

在 `server/main.py` 中添加：

```python
from server.api.v1.anthropic import router as anthropic_router

app.include_router(anthropic_router)
```

### 步骤 3: 测试验证

1. **非流式请求测试**
```bash
curl -X POST http://localhost:38520/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: your-api-key" \
  -d '{
    "model": "claude-3-sonnet-20240229",
    "max_tokens": 1024,
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

2. **流式请求测试**
```bash
curl -X POST http://localhost:38520/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: your-api-key" \
  -d '{
    "model": "claude-3-sonnet-20240229",
    "max_tokens": 1024,
    "messages": [{"role": "user", "content": "Hello!"}],
    "stream": true
  }'
```

## 扩展性考虑

1. **多模型支持**: 通过 `model_mapping.py` 可以轻松添加更多模型映射
2. **工具调用**: 可以扩展支持 Anthropic 的 tool_use 功能
3. **图像输入**: 可以扩展支持 vision 模型的图像输入
4. **错误处理**: 统一错误格式转换

## 注意事项

1. **API Key 处理**: Anthropic 使用 `x-api-key` 头，OpenAI 使用 `Authorization: Bearer` 头
2. **Token 计算**: 两种 API 的 token 计算方式可能不同，需要确保 usage 字段正确
3. **超时设置**: 流式响应需要适当的超时处理
4. **并发处理**: 确保适配器不会成为性能瓶颈
