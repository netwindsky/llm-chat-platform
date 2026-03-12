import os
import sys
from contextlib import asynccontextmanager

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_ROOT)

sys.path.insert(0, PROJECT_ROOT)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from server.core.manager import ModelManager
from server.services.backend_manager import BackendManager
from server.api.v1 import models, chat, openai, logs, anthropic
from server.middleware.logging import RequestLoggingMiddleware


# 全局变量
model_manager: ModelManager = None
backend_manager: BackendManager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global model_manager, backend_manager
    
    # 启动时初始化
    print("Initializing LLM Platform...")
    
    # 初始化模型管理器
    config_path = "configs/models.yaml"
    model_manager = ModelManager(config_path)
    print(f"Loaded {len(model_manager.models)} models")

    # 设置全局模型管理器（供适配器使用）
    from server.core.manager import set_global_model_manager
    set_global_model_manager(model_manager)
    
    # 初始化后端管理器
    backend_manager = BackendManager({
        "model_loading": {
            "max_loaded_models": 3
        }
    })

    # 设置全局后端管理器（供适配器使用）
    from server.services.backend_manager import set_global_backend_manager
    set_global_backend_manager(backend_manager)
    
    # 注入到 API 路由
    models.set_managers(model_manager, backend_manager)
    chat.set_backend_manager(backend_manager)
    chat.set_model_manager(model_manager)
    openai.set_managers(backend_manager, model_manager)
    
    print("LLM Platform initialized successfully!")
    
    yield
    
    # 关闭时清理
    print("Shutting down...")
    await backend_manager.shutdown()


# 创建 FastAPI 应用
app = FastAPI(
    title="LLM 推理平台 API",
    description="统一的大语言模型推理平台，支持多模型切换",
    version="1.0.0",
    lifespan=lifespan
)

# 请求日志中间件（必须在 CORS 之前）
app.add_middleware(RequestLoggingMiddleware)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 注册路由
app.include_router(models.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(logs.router, prefix="/api/v1")
# OpenAI 兼容路由 (标准 /v1 路径)
app.include_router(openai.router, prefix="/v1")
# Anthropic 兼容路由 (标准 /v1 路径)
app.include_router(anthropic.router, prefix="/v1")
# Anthropic 兼容路由 (处理 /v1/v1 重复前缀的情况)
app.include_router(anthropic.router, prefix="/v1/v1")

# 打印所有注册的路由（用于调试）
print("\n[ROUTES] Registered routes:")
for route in app.routes:
    if hasattr(route, 'methods') and hasattr(route, 'path'):
        print(f"  {route.methods} {route.path}")


@app.get("/")
async def root():
    return {
        "name": "LLM 推理平台",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "models_loaded": len(backend_manager.get_loaded_models()) if backend_manager else 0
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=38520, help="API server port")
    args = parser.parse_args()
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=args.port,
        reload=False,
        timeout_keep_alive=300,
        timeout_graceful_shutdown=30
    )
