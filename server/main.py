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
from server.api.v1 import models, chat, openai, logs, anthropic, admin
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
    
    # 加载服务器配置
    import yaml
    server_config = {}
    try:
        with open("configs/server.yaml", "r", encoding="utf-8") as f:
            server_config = yaml.safe_load(f) or {}
    except Exception as e:
        print(f"[Warning] 无法加载 server.yaml: {e}")
    
    # 初始化后端管理器（传入完整配置）
    backend_manager = BackendManager({
        "model_loading": {
            "max_loaded_models": 3
        },
        "idle_monitor": server_config.get("idle_monitor", {"enabled": True, "timeout": 60})
    })

    # 设置全局后端管理器（供适配器使用）
    from server.services.backend_manager import set_global_backend_manager
    set_global_backend_manager(backend_manager)
    
    # 注入到 API 路由
    models.set_managers(model_manager, backend_manager)
    chat.set_backend_manager(backend_manager)
    chat.set_model_manager(model_manager)
    openai.set_managers(backend_manager, model_manager)
    
    # 注入到管理API
    from server.services.idle_monitor import get_idle_monitor
    admin.set_managers(model_manager, backend_manager, get_idle_monitor())
    
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
app.include_router(admin.router, prefix="/api/v1")
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


@app.get("/unload")
async def unload_all_models():
    """直接卸载所有已加载的模型（根路径快捷接口）GET 方法"""
    if not backend_manager or not model_manager:
        return {"success": False, "error": "Managers not initialized"}
    
    try:
        loaded_models = backend_manager.get_loaded_models()
        unloaded_models = []
        failed_models = []
        
        for model_id in loaded_models:
            try:
                await backend_manager.unload_model(model_id)
                model_manager.update_model_status(model_id, "unloaded")
                unloaded_models.append(model_id)
            except Exception as e:
                failed_models.append({"model_id": model_id, "error": str(e)})
        
        return {
            "success": True,
            "message": f"Unloaded {len(unloaded_models)} models",
            "unloaded_models": unloaded_models,
            "failed_models": failed_models
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


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
