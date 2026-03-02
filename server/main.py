import os
import sys
from contextlib import asynccontextmanager

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from server.core.manager import ModelManager
from server.services.backend_manager import BackendManager
from server.api.v1 import models, chat


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
    model_manager = ModelManager("configs/models.yaml")
    print(f"Loaded {len(model_manager.models)} models")
    
    # 初始化后端管理器
    backend_manager = BackendManager({
        "model_loading": {
            "max_loaded_models": 3
        }
    })
    
    # 注入到 API 路由
    models.set_managers(model_manager, backend_manager)
    chat.set_backend_manager(backend_manager)
    
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
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=False
    )
