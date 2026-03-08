"""
请求追踪日志系统
用于记录完整的请求/响应流程，便于前后端联调分析
"""

import json
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
from contextvars import ContextVar

# 请求追踪ID上下文变量
request_id_var: ContextVar[str] = ContextVar('request_id', default='')


class RequestLogger:
    """请求追踪日志记录器"""

    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.request_log = self.log_dir / "requests.log"

    def generate_request_id(self) -> str:
        """生成唯一的请求追踪ID"""
        return f"req_{uuid.uuid4().hex[:16]}_{int(time.time() * 1000) % 10000}"

    def set_request_id(self, request_id: str):
        """设置当前请求的追踪ID"""
        request_id_var.set(request_id)

    def get_request_id(self) -> str:
        """获取当前请求的追踪ID"""
        return request_id_var.get()

    def log_request_start(
        self,
        request_id: str,
        client_ip: str,
        method: str,
        path: str,
        headers: Dict[str, str],
        body: Any,
        **extra
    ):
        """记录请求开始"""
        self.set_request_id(request_id)

        # 过滤敏感信息
        safe_headers = self._filter_sensitive_headers(headers)
        safe_body = self._filter_sensitive_body(body)

        data = {
            "timestamp": datetime.now().isoformat(),
            "request_id": request_id,
            "phase": "start",
            "client_ip": client_ip,
            "method": method,
            "path": path,
            "headers": safe_headers,
            "body": safe_body,
            "extra": extra
        }

        self._write_log("REQUEST_START", data)

        # 同时输出到控制台（便于开发调试）
        print(f"\n[REQUEST] {request_id} | {method} {path} | IP: {client_ip}")
        if extra.get('model'):
            print(f"          Model: {extra['model']}, Stream: {extra.get('stream', 'unknown')}")

    def log_request_end(
        self,
        request_id: str,
        status_code: int,
        duration_ms: float,
        response_body: Any = None,
        error: str = None,
        **extra
    ):
        """记录请求结束"""
        data = {
            "timestamp": datetime.now().isoformat(),
            "request_id": request_id,
            "phase": "end",
            "status_code": status_code,
            "duration_ms": round(duration_ms, 2),
            "response_summary": self._summarize_response(response_body),
            "error": error,
            "extra": extra
        }

        self._write_log("REQUEST_END", data)

        # 输出到控制台
        status_icon = "✓" if status_code < 400 else "✗"
        print(f"[RESPONSE] {request_id} | {status_icon} {status_code} | {duration_ms:.2f}ms")
        if error:
            print(f"           Error: {error}")
        print()

    def log_backend_request(
        self,
        backend_name: str,
        operation: str,
        request_data: Dict[str, Any],
        **extra
    ):
        """记录后端请求"""
        request_id = self.get_request_id()

        data = {
            "timestamp": datetime.now().isoformat(),
            "request_id": request_id,
            "phase": "backend_request",
            "backend": backend_name,
            "operation": operation,
            "request_data": request_data,
            "extra": extra
        }

        self._write_log("BACKEND_REQ", data)
        print(f"[BACKEND] {request_id} | {backend_name}.{operation}")

    def log_backend_response(
        self,
        backend_name: str,
        operation: str,
        status: str,
        duration_ms: float,
        response_data: Any = None,
        error: str = None,
        **extra
    ):
        """记录后端响应"""
        request_id = self.get_request_id()

        data = {
            "timestamp": datetime.now().isoformat(),
            "request_id": request_id,
            "phase": "backend_response",
            "backend": backend_name,
            "operation": operation,
            "status": status,
            "duration_ms": round(duration_ms, 2),
            "response_summary": self._summarize_response(response_data),
            "error": error,
            "extra": extra
        }

        self._write_log("BACKEND_RESP", data)
        status_icon = "✓" if status == "success" else "✗"
        print(f"[BACKEND] {request_id} | {backend_name}.{operation} | {status_icon} {status} | {duration_ms:.2f}ms")

    def log_stream_chunk(self, chunk_index: int, chunk_data: Dict[str, Any]):
        """记录流式响应的 chunk（仅记录摘要，不记录完整内容）"""
        request_id = self.get_request_id()

        # 提取关键信息
        delta = chunk_data.get("choices", [{}])[0].get("delta", {})
        content_preview = (delta.get("content", "") or delta.get("thinking", ""))[:50]

        data = {
            "timestamp": datetime.now().isoformat(),
            "request_id": request_id,
            "phase": "stream_chunk",
            "chunk_index": chunk_index,
            "content_preview": content_preview,
            "has_content": bool(delta.get("content")),
            "has_thinking": bool(delta.get("thinking") or delta.get("reasoning_content"))
        }

        self._write_log("STREAM_CHUNK", data)

    def _write_log(self, log_type: str, data: Dict[str, Any]):
        """写入日志文件"""
        try:
            with open(self.request_log, 'a', encoding='utf-8') as f:
                f.write(f"{log_type} | {json.dumps(data, ensure_ascii=False)}\n")
        except Exception as e:
            print(f"[RequestLogger] Failed to write log: {e}")

    def _filter_sensitive_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """过滤敏感请求头"""
        sensitive = ['authorization', 'cookie', 'x-api-key', 'api-key']
        return {
            k: v if k.lower() not in sensitive else '***'
            for k, v in headers.items()
        }

    def _filter_sensitive_body(self, body: Any) -> Any:
        """过滤敏感请求体内容"""
        if not isinstance(body, dict):
            return body

        # 复制一份避免修改原数据
        safe_body = dict(body)

        # 过滤敏感字段
        sensitive_fields = ['api_key', 'apikey', 'token', 'password', 'secret']
        for field in sensitive_fields:
            if field in safe_body:
                safe_body[field] = '***'

        # 对于聊天请求，记录消息数量而不是完整内容
        if 'messages' in safe_body and isinstance(safe_body['messages'], list):
            safe_body['messages_count'] = len(safe_body['messages'])
            # 只记录最后一条消息的预览
            if safe_body['messages']:
                last_msg = safe_body['messages'][-1]
                if isinstance(last_msg, dict):
                    content = last_msg.get('content', '')
                    if isinstance(content, str):
                        safe_body['last_message_preview'] = content[:100] + '...' if len(content) > 100 else content
            del safe_body['messages']

        return safe_body

    def _summarize_response(self, response: Any) -> Dict[str, Any]:
        """总结响应内容"""
        if not response:
            return {}

        if isinstance(response, dict):
            summary = {}

            # 提取关键字段
            if 'choices' in response:
                summary['choices_count'] = len(response['choices'])
                if response['choices']:
                    choice = response['choices'][0]
                    if 'message' in choice:
                        content = choice['message'].get('content', '')
                        summary['content_length'] = len(content)
                        summary['content_preview'] = content[:100] + '...' if len(content) > 100 else content
                    if 'delta' in choice:
                        delta = choice['delta']
                        summary['has_delta'] = True
                        summary['delta_content_length'] = len(delta.get('content', ''))

            if 'usage' in response:
                summary['usage'] = response['usage']

            if 'model' in response:
                summary['model'] = response['model']

            return summary

        return {"type": type(response).__name__}

    def get_request_trace(self, request_id: str) -> List[Dict[str, Any]]:
        """获取特定请求的完整追踪记录"""
        traces = []
        try:
            with open(self.request_log, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        if request_id in line:
                            parts = line.split(' | ', 1)
                            if len(parts) == 2:
                                log_type, data = parts
                                traces.append({
                                    "type": log_type,
                                    "data": json.loads(data)
                                })
                    except:
                        continue
        except Exception as e:
            print(f"[RequestLogger] Failed to read trace: {e}")

        return traces


# 全局实例
_request_logger = RequestLogger()


def get_request_logger() -> RequestLogger:
    """获取请求日志记录器实例"""
    return _request_logger


def generate_request_id() -> str:
    """生成请求追踪ID"""
    return _request_logger.generate_request_id()


def set_request_id(request_id: str):
    """设置当前请求ID"""
    _request_logger.set_request_id(request_id)


def get_request_id() -> str:
    """获取当前请求ID"""
    return _request_logger.get_request_id()
