"""
FastAPI 请求日志中间件
自动记录所有请求的详细信息
"""

import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import json

from ..utils.request_logger import get_request_logger, generate_request_id


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志记录中间件"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 生成请求追踪ID
        request_id = generate_request_id()

        # 获取客户端IP
        client_ip = request.headers.get('x-forwarded-for', request.client.host if request.client else 'unknown')

        # 获取请求头
        headers = dict(request.headers)

        # 记录请求开始
        logger = get_request_logger()
        
        # 尝试获取请求体信息（不读取 body，避免影响流式响应）
        extra_info = {}
        try:
            content_type = request.headers.get('content-type', '')
            if 'application/json' in content_type and request.method in ['POST', 'PUT', 'PATCH']:
                # 只记录基本信息，不读取 body
                extra_info['content_type'] = content_type
                extra_info['content_length'] = request.headers.get('content-length')
        except:
            pass

        logger.log_request_start(
            request_id=request_id,
            client_ip=client_ip,
            method=request.method,
            path=request.url.path,
            headers=headers,
            body=None,  # 不记录 body，避免影响流式响应
            **extra_info
        )

        # 记录开始时间
        start_time = time.time()

        try:
            # 处理请求
            response = await call_next(request)

            # 计算耗时
            duration_ms = (time.time() - start_time) * 1000

            # 记录请求结束
            logger.log_request_end(
                request_id=request_id,
                status_code=response.status_code,
                duration_ms=duration_ms
            )

            # 添加请求ID到响应头（便于前端关联日志）
            response.headers['X-Request-ID'] = request_id

            return response

        except Exception as e:
            # 计算耗时
            duration_ms = (time.time() - start_time) * 1000

            # 记录错误
            logger.log_request_end(
                request_id=request_id,
                status_code=500,
                duration_ms=duration_ms,
                error=str(e)
            )

            raise
