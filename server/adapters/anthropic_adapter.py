"""
Anthropic API 适配器
将 Anthropic API 请求转换为 OpenAI API 请求，并将响应转换回 Anthropic 格式
"""

import json
import uuid
from typing import Dict, List, Optional, Any, AsyncGenerator, Union
from datetime import datetime

from .model_mapping import map_anthropic_to_openai_model, map_openai_to_anthropic_model


class AnthropicRequestConverter:
    """Anthropic 请求转换为 OpenAI 请求"""

    @staticmethod
    def convert_messages(anthropic_messages: List[Dict], system: Optional[Union[str, List]] = None, tools: Optional[List[Dict]] = None) -> List[Dict]:
        """
        将 Anthropic 消息格式转换为 OpenAI 消息格式

        Anthropic: messages 只包含 user/assistant，system 是独立字段
        OpenAI: messages 包含 system/user/assistant
        """
        openai_messages = []

        # 构建 system message
        # system 可能是字符串或列表（Anthropic 支持两种格式）
        if isinstance(system, list):
            # 如果 system 是列表，提取所有 text 类型的内容
            system_parts = []
            for part in system:
                if isinstance(part, dict) and part.get("type") == "text":
                    system_parts.append(part.get("text", ""))
                elif isinstance(part, str):
                    system_parts.append(part)
            system_content = "\n".join(system_parts)
        else:
            system_content = system or ""
        
        # 如果有 tools，将工具信息添加到 system message（Qwen 需要这种格式）
        if tools:
            tools_prompt = "\n\n# Tools\n\nYou may call one or more functions to assist with the user query.\n\nYou are provided with function signatures within <tools></tools> XML tags:\n<tools>"
            for tool in tools:
                tool_name = tool.get("name", "")
                tool_desc = tool.get("description", "")
                tool_schema = tool.get("input_schema", {})
                tools_prompt += f'\n<tool>\n<name>{tool_name}</name>\n<description>{tool_desc}</description>\n<parameters>{json.dumps(tool_schema)}</parameters>\n</tool>'
            tools_prompt += "\n</tools>\n\nFor each function call, return a json object with function name and arguments within <tool_use></tool_use> XML tags:\n<tool_use>\n<name>function_name</name>\n<arguments>{\"arg1\": \"value1\", \"arg2\": \"value2\"}</arguments>\n</tool_use>"
            system_content += tools_prompt
        
        # 添加 system message
        if system_content:
            openai_messages.append({
                "role": "system",
                "content": system_content
            })

        # 转换 user/assistant messages
        for msg in anthropic_messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # Anthropic 支持 content 数组格式，需要转换
            if isinstance(content, list):
                # 提取文本内容（只保留 text 类型，去除 cache_control 等不支持的字段）
                text_parts = []
                for part in content:
                    if part.get("type") == "text":
                        text_parts.append(part.get("text", ""))
                    elif part.get("type") == "tool_use":
                        # 转换 tool_use 为模型可理解的格式
                        tool_name = part.get("name", "")
                        tool_input = part.get("input", {})
                        text_parts.append(f'<tool_use>\n<name>{tool_name}</name>\n<arguments>{json.dumps(tool_input)}</arguments>\n</tool_use>')
                    elif part.get("type") == "tool_result":
                        # 转换 tool_result 为模型可理解的格式
                        tool_result = part.get("content", "")
                        text_parts.append(f"<tool_result>\n{tool_result}\n</tool_result>")
                    # 忽略其他类型（如 cache_control）
                content = "\n".join(text_parts)

            openai_messages.append({
                "role": role,
                "content": content
            })

        return openai_messages

    @staticmethod
    def convert_request(anthropic_body: Dict) -> Dict:
        """
        将 Anthropic 请求体转换为 OpenAI 请求体
        """
        # 获取映射后的模型名
        anthropic_model = anthropic_body.get("model", "claude-3-sonnet-20240229")
        openai_model = map_anthropic_to_openai_model(anthropic_model)

        # 获取 tools
        tools = anthropic_body.get("tools", [])
        
        # 构建 OpenAI 请求体
        openai_body = {
            "model": openai_model,
            "messages": AnthropicRequestConverter.convert_messages(
                anthropic_body.get("messages", []),
                anthropic_body.get("system"),
                tools  # 传递 tools 用于构建 system prompt
            ),
            "max_tokens": anthropic_body.get("max_tokens", 1024),
            "temperature": anthropic_body.get("temperature", 0.7),
            "stream": anthropic_body.get("stream", False)
        }

        # 可选参数
        if "top_p" in anthropic_body:
            openai_body["top_p"] = anthropic_body["top_p"]

        if "top_k" in anthropic_body:
            openai_body["top_k"] = anthropic_body["top_k"]

        # Anthropic 的 stop_sequences 对应 OpenAI 的 stop
        if "stop_sequences" in anthropic_body:
            openai_body["stop"] = anthropic_body["stop_sequences"]

        # 转换 tools 参数
        if "tools" in anthropic_body:
            openai_body["tools"] = AnthropicRequestConverter.convert_tools(anthropic_body["tools"])

        return openai_body

    @staticmethod
    def convert_tools(anthropic_tools: List[Dict]) -> List[Dict]:
        """
        将 Anthropic tools 转换为 OpenAI tools 格式

        Anthropic: {"name": "...", "description": "...", "input_schema": {...}}
        OpenAI: {"type": "function", "function": {"name": "...", "description": "...", "parameters": {...}}}
        """
        openai_tools = []
        for tool in anthropic_tools:
            openai_tool = {
                "type": "function",
                "function": {
                    "name": tool.get("name", ""),
                    "description": tool.get("description", ""),
                    "parameters": tool.get("input_schema", {"type": "object", "properties": {}})
                }
            }
            openai_tools.append(openai_tool)
        return openai_tools


class AnthropicResponseConverter:
    """OpenAI 响应转换为 Anthropic 响应"""

    @staticmethod
    def map_finish_reason(openai_reason: Optional[str]) -> str:
        """
        映射 finish reason

        OpenAI: stop, length, content_filter, tool_calls
        Anthropic: end_turn, max_tokens, stop_sequence, tool_use
        """
        mapping = {
            "stop": "end_turn",
            "length": "max_tokens",
            "content_filter": "content_filter",
            "tool_calls": "tool_use"
        }
        return mapping.get(openai_reason, "end_turn")

    @staticmethod
    def parse_xml_tool_calls(content: str) -> List[Dict]:
        """
        解析 XML 格式的工具调用

        Qwen 模型可能输出格式（支持多种变体）：
        <tool_use>
        <name>tool_name</name>
        <arguments>{"key": "value"}</arguments>
        </tool_use>
        
        <tool-use>
        <name>tool_name</name>
        <arguments>{"key": "value"}</arguments>
        </tool-use>
        
        <tool use>
        <name>tool_name</name>
        <arguments>{"key": "value"}</arguments>
        </tool use>

        返回 Anthropic 格式的 tool_use 列表
        """
        import re
        tool_uses = []

        # 支持多种 tool_use 标签格式（下划线、连字符、空格）
        patterns = [
            # <tool_use>...</tool_use>
            r'<tool_use>\s*<name>(.*?)</name>\s*<arguments>(.*?)</arguments>\s*</tool_use>',
            # <tool-use>...</tool-use>
            r'<tool-use>\s*<name>(.*?)</name>\s*<arguments>(.*?)</arguments>\s*</tool-use>',
            # <tool use>...</tool use>
            r'<tool use>\s*<name>(.*?)</name>\s*<arguments>(.*?)</arguments>\s*</tool use>',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.DOTALL)
            for i, (name, args_str) in enumerate(matches):
                try:
                    # 解析参数 JSON
                    args = json.loads(args_str.strip())
                    tool_uses.append({
                        "type": "tool_use",
                        "id": f"toolu_{len(tool_uses)}",
                        "name": name.strip(),
                        "input": args
                    })
                except json.JSONDecodeError:
                    # 如果解析失败，跳过这个工具调用
                    continue

        return tool_uses

    @staticmethod
    def convert_completion(openai_response: Dict, anthropic_model: str) -> Dict:
        """
        将 OpenAI 非流式响应转换为 Anthropic 响应
        """
        # 处理错误响应
        if "error" in openai_response:
            return {
                "type": "error",
                "error": {
                    "type": "api_error",
                    "message": openai_response["error"].get("message", "Unknown error")
                }
            }

        choice = openai_response.get("choices", [{}])[0]
        message = choice.get("message", {})
        usage = openai_response.get("usage", {})

        # 构建 content 数组（处理 text 和 tool_use）
        content = []

        # 添加文本内容
        text_content = message.get("content", "")

        # 解析 XML 格式的工具调用（llama-server 可能返回这种格式）
        tool_uses = []
        if text_content:
            tool_uses = AnthropicResponseConverter.parse_xml_tool_calls(text_content)

        if tool_uses:
            # 如果有工具调用，提取文本部分和工具调用
            # 找到第一个 <tool_use> 之前的文本
            tool_use_start = text_content.find("<tool_use>")
            if tool_use_start > 0:
                text_part = text_content[:tool_use_start].strip()
                if text_part:
                    content.append({
                        "type": "text",
                        "text": text_part
                    })
            # 添加工具调用
            for tool_use in tool_uses:
                content.append(tool_use)
        elif text_content:
            content.append({
                "type": "text",
                "text": text_content
            })

        # 转换 OpenAI 标准格式的 tool_calls 为 tool_use
        tool_calls = message.get("tool_calls", [])
        for tool_call in tool_calls:
            content.append({
                "type": "tool_use",
                "id": tool_call.get("id", ""),
                "name": tool_call.get("function", {}).get("name", ""),
                "input": json.loads(tool_call.get("function", {}).get("arguments", "{}"))
            })

        # 确定 stop_reason
        # 如果有工具调用，stop_reason 应该是 "tool_use"
        if tool_uses or tool_calls:
            stop_reason = "tool_use"
        else:
            stop_reason = AnthropicResponseConverter.map_finish_reason(
                choice.get('finish_reason')
            )

        # 构建 Anthropic 响应
        anthropic_response = {
            "id": f"msg_{openai_response.get('id', str(uuid.uuid4()))[-12:]}",
            "type": "message",
            "role": "assistant",
            "model": anthropic_model,
            "content": content,
            "stop_reason": stop_reason,
            "stop_sequence": None,
            "usage": {
                "input_tokens": usage.get('prompt_tokens', 0),
                "output_tokens": usage.get('completion_tokens', 0)
            }
        }

        return anthropic_response


class AnthropicStreamConverter:
    """OpenAI 流式响应转换为 Anthropic 流式响应"""

    def __init__(self, anthropic_model: str):
        self.anthropic_model = anthropic_model
        self.message_id = None
        self.started = False

    def convert_chunk(self, openai_chunk: Dict) -> List[Dict]:
        """
        将 OpenAI 流式块转换为 Anthropic SSE 事件列表
        """
        events = []

        # 处理错误
        if "error" in openai_chunk:
            events.append({
                "event": "error",
                "data": json.dumps({
                    "type": "error",
                    "error": openai_chunk["error"]
                })
            })
            return events

        choices = openai_chunk.get("choices", [])
        if not choices:
            return events

        choice = choices[0]
        delta = choice.get("delta", {})

        # 第一个块：发送 message_start 和 content_block_start
        if not self.started:
            self.started = True
            self.message_id = f"msg_{openai_chunk.get('id', str(uuid.uuid4()))[-12:]}"

            # message_start 事件
            events.append({
                "event": "message_start",
                "data": json.dumps({
                    "type": "message_start",
                    "message": {
                        "id": self.message_id,
                        "type": "message",
                        "role": "assistant",
                        "model": self.anthropic_model,
                        "content": []
                    }
                })
            })

            # content_block_start 事件
            events.append({
                "event": "content_block_start",
                "data": json.dumps({
                    "type": "content_block_start",
                    "index": 0,
                    "content_block": {
                        "type": "text",
                        "text": ""
                    }
                })
            })

        # 内容增量
        content = delta.get("content", "")
        if content:
            events.append({
                "event": "content_block_delta",
                "data": json.dumps({
                    "type": "content_block_delta",
                    "index": 0,
                    "delta": {
                        "type": "text_delta",
                        "text": content
                    }
                })
            })

        # 结束块
        finish_reason = choice.get("finish_reason")
        if finish_reason:
            # content_block_stop
            events.append({
                "event": "content_block_stop",
                "data": json.dumps({
                    "type": "content_block_stop",
                    "index": 0
                })
            })

            # message_delta（包含 stop_reason 和 usage）
            events.append({
                "event": "message_delta",
                "data": json.dumps({
                    "type": "message_delta",
                    "delta": {
                        "stop_reason": AnthropicResponseConverter.map_finish_reason(finish_reason),
                        "stop_sequence": None
                    },
                    "usage": {
                        "output_tokens": openai_chunk.get("usage", {}).get("completion_tokens", 0)
                    }
                })
            })

            # message_stop
            events.append({
                "event": "message_stop",
                "data": json.dumps({
                    "type": "message_stop"
                })
            })

        return events


class AnthropicAdapter:
    """
    Anthropic API 适配器主类
    """

    def __init__(self):
        self.request_converter = AnthropicRequestConverter()
        self.response_converter = AnthropicResponseConverter()

    def convert_request(self, anthropic_body: Dict) -> Dict:
        """转换请求"""
        return self.request_converter.convert_request(anthropic_body)

    def convert_response(self, openai_response: Dict, anthropic_model: str) -> Dict:
        """转换响应"""
        return self.response_converter.convert_completion(openai_response, anthropic_model)

    def create_stream_converter(self, anthropic_model: str) -> AnthropicStreamConverter:
        """创建流式转换器"""
        return AnthropicStreamConverter(anthropic_model)
