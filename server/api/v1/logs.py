"""
前端日志接收 API
接收并保存前端发送的日志
"""

from fastapi import APIRouter, Request
from typing import List, Dict, Any
from datetime import datetime
from pathlib import Path
import json

router = APIRouter(prefix="/logs", tags=["logs"])

# 前端日志文件
LOG_DIR = Path("logs")
FRONTEND_LOG = LOG_DIR / "frontend.log"

# 确保日志目录存在
LOG_DIR.mkdir(exist_ok=True)


@router.post("/frontend")
async def receive_frontend_logs(request: Request):
    """接收前端日志"""
    try:
        data = await request.json()
        logs = data.get('logs', [])
        
        # 获取请求信息
        client_ip = request.headers.get('x-forwarded-for', request.client.host if request.client else 'unknown')
        user_agent = request.headers.get('user-agent', 'unknown')
        
        # 写入日志文件
        with open(FRONTEND_LOG, 'a', encoding='utf-8') as f:
            for log in logs:
                # 添加后端接收信息
                enriched_log = {
                    **log,
                    'received_at': datetime.now().isoformat(),
                    'client_ip': client_ip,
                    'user_agent': user_agent
                }
                f.write(f"FRONTEND | {json.dumps(enriched_log, ensure_ascii=False)}\n")
        
        return {"status": "ok", "received": len(logs)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/frontend")
async def get_frontend_logs(limit: int = 100):
    """获取前端日志（用于调试）"""
    try:
        if not FRONTEND_LOG.exists():
            return {"logs": []}
        
        with open(FRONTEND_LOG, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 解析日志
        logs = []
        for line in lines[-limit:]:
            try:
                if ' | ' in line:
                    _, data = line.split(' | ', 1)
                    logs.append(json.loads(data))
            except:
                continue
        
        return {"logs": logs, "total": len(lines)}
    except Exception as e:
        return {"error": str(e)}


@router.delete("/frontend")
async def clear_frontend_logs():
    """清空前端日志"""
    try:
        if FRONTEND_LOG.exists():
            FRONTEND_LOG.unlink()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
