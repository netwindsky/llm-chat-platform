from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

router = APIRouter(prefix="/models", tags=["模型管理"])


class ModelLoadRequest(BaseModel):
    model_id: Optional[str] = None
    gpu_layers: Optional[int] = 99
    context_size: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None


class ModelInfoResponse(BaseModel):
    id: str
    name: str
    type: str
    category: str
    format: str
    size: str
    quantization: str
    backend: str
    max_context: int
    default_temp: float
    default_top_p: float
    tags: List[str]
    description: str
    status: str
    file_exists: bool
    memory_usage: Optional[float] = None


class ModelListResponse(BaseModel):
    models: List[Dict[str, Any]]
    total: int


# 模型管理器实例（将在 main.py 中注入）
_model_manager = None
_backend_manager = None


def get_model_manager():
    return _model_manager


def get_backend_manager():
    return _backend_manager


def set_managers(model_manager, backend_manager):
    global _model_manager, _backend_manager
    _model_manager = model_manager
    _backend_manager = backend_manager


@router.get("/", response_model=ModelListResponse)
async def list_models(
    model_type: Optional[str] = None,
    category: Optional[str] = None,
    loaded_only: bool = False
):
    """获取模型列表"""
    model_manager = get_model_manager()
    if not model_manager:
        raise HTTPException(status_code=500, detail="Model manager not initialized")
    
    models = model_manager.list_models(
        model_type=model_type,
        category=category,
        loaded_only=loaded_only
    )
    
    model_types = model_manager.get_types()
    
    result = []
    for m in models:
        type_info = model_types.get(m.type, {})
        result.append({
            "id": m.id,
            "name": m.name,
            "type": m.type,
            "category": m.category,
            "format": m.format,
            "size": m.size,
            "quantization": m.quantization,
            "backend": m.backend,
            "max_context": m.max_context,
            "default_temp": m.default_temp,
            "default_top_p": m.default_top_p,
            "tags": m.tags,
            "description": m.description,
            "status": m.status,
            "file_exists": m.file_exists,
            "memory_usage": m.memory_usage,
            "type_info": {
                "icon": type_info.icon,
                "color": type_info.color,
                "description": type_info.description
            }
        })
    
    return {"models": result, "total": len(result)}


@router.get("/types")
async def get_model_types():
    """获取模型类型列表"""
    model_manager = get_model_manager()
    if not model_manager:
        raise HTTPException(status_code=500, detail="Model manager not initialized")
    
    types = model_manager.get_types()
    return {
        "types": [
            {
                "id": k,
                "icon": v.icon,
                "color": v.color,
                "description": v.description,
                "count": len([m for m in model_manager.models.values() if m.type == k])
            }
            for k, v in types.items()
        ]
    }


@router.get("/{model_id}", response_model=ModelInfoResponse)
async def get_model(model_id: str):
    """获取模型详情"""
    model_manager = get_model_manager()
    if not model_manager:
        raise HTTPException(status_code=500, detail="Model manager not initialized")
    
    model = model_manager.get_model(model_id)
    if not model:
        raise HTTPException(status_code=404, detail=f"Model not found: {model_id}")
    
    # 检查后端管理器中的实时状态
    backend_manager = get_backend_manager()
    if backend_manager and model_id in backend_manager.get_loaded_models():
        # 从后端实例获取实时状态
        backend = backend_manager._loaded_models.get(model_id)
        if backend and backend._model_info:
            old_status = model.status
            model.status = backend._model_info.status.value
            print(f"get_model {model_id}: backend status={model.status} (was {old_status})")
        else:
            print(f"get_model {model_id}: backend exists but _model_info is None")
    else:
        print(f"get_model {model_id}: not in loaded_models, status={model.status}")
    
    return ModelInfoResponse(
        id=model.id,
        name=model.name,
        type=model.type,
        category=model.category,
        format=model.format,
        size=model.size,
        quantization=model.quantization,
        backend=model.backend,
        max_context=model.max_context,
        default_temp=model.default_temp,
        default_top_p=model.default_top_p,
        tags=model.tags,
        description=model.description,
        status=model.status,
        file_exists=model.file_exists,
        memory_usage=model.memory_usage
    )


@router.post("/{model_id}/load")
async def load_model(model_id: str, request: ModelLoadRequest = None):
    """加载模型"""
    model_manager = get_model_manager()
    backend_manager = get_backend_manager()
    
    if not model_manager or not backend_manager:
        raise HTTPException(status_code=500, detail="Managers not initialized")
    
    model = model_manager.get_model(model_id)
    if not model:
        raise HTTPException(status_code=404, detail=f"Model not found: {model_id}")
    
    if not model.file_exists:
        raise HTTPException(status_code=400, detail=f"Model file not found: {model.path}")
    
    # 使用默认值或请求中的值
    gpu_layers = request.gpu_layers if request and request.gpu_layers is not None else 99
    context_size = request.context_size if request and request.context_size else None
    temperature = request.temperature if request and request.temperature else None
    top_p = request.top_p if request and request.top_p else None
    
    try:
        # 先将所有已加载的模型状态设为 unloaded（因为只支持单模型）
        for m in model_manager.list_models():
            if m.status == "loaded" and m.id != model_id:
                model_manager.update_model_status(m.id, "unloaded")
        
        success = await backend_manager.load_model(
            model_id,
            model.path,
            {
                "id": model.id,
                "name": model.name,
                "type": model.type,
                "category": model.category,
                "max_context": context_size or model.max_context,
                "gpu_layers": gpu_layers,
                "temperature": temperature or model.default_temp,
                "top_p": top_p or model.default_top_p,
                "default_temp": model.default_temp,
                "default_top_p": model.default_top_p,
                "tags": model.tags,
                "description": model.description
            }
        )
        
        if success:
            model_manager.update_model_status(model_id, "loaded")
            return {"success": True, "message": f"Model {model_id} loaded successfully"}
        else:
            model_manager.update_model_status(model_id, "error")
            return {"success": False, "message": f"Failed to load model {model_id}"}
            
    except Exception as e:
        model_manager.update_model_status(model_id, "error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{model_id}/unload")
async def unload_model(model_id: str):
    """卸载模型"""
    model_manager = get_model_manager()
    backend_manager = get_backend_manager()
    
    if not model_manager or not backend_manager:
        raise HTTPException(status_code=500, detail="Managers not initialized")
    
    try:
        await backend_manager.unload_model(model_id)
        model_manager.update_model_status(model_id, "unloaded")
        return {"success": True, "message": f"Model {model_id} unloaded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
