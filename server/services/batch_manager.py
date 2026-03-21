"""
批处理任务管理服务
用于管理 OpenAI Batches API 的批处理任务
"""

import uuid
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

# 批处理存储目录
BATCHES_DIR = Path("data/batches")
METADATA_FILE = BATCHES_DIR / "metadata.json"


class BatchManager:
    """批处理任务管理器"""
    
    def __init__(self):
        self.batches_dir = BATCHES_DIR
        self.metadata_file = METADATA_FILE
        self.batches: Dict[str, Dict[str, Any]] = {}
        self._load_metadata()
    
    def _ensure_dirs(self):
        """确保存储目录存在"""
        self.batches_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_metadata(self):
        """加载元数据"""
        self._ensure_dirs()
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, "r", encoding="utf-8") as f:
                    self.batches = json.load(f)
            except Exception as e:
                print(f"[BatchManager] Failed to load metadata: {e}")
                self.batches = {}
        else:
            self.batches = {}
    
    def _save_metadata(self):
        """保存元数据"""
        self._ensure_dirs()
        try:
            with open(self.metadata_file, "w", encoding="utf-8") as f:
                json.dump(self.batches, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[BatchManager] Failed to save metadata: {e}")
    
    def create_batch(
        self,
        input_file_id: str,
        endpoint: str,
        completion_window: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        创建批处理任务
        
        Args:
            input_file_id: 输入文件 ID
            endpoint: 端点（如 /v1/chat/completions）
            completion_window: 完成时间窗口（如 24h）
            metadata: 元数据
            
        Returns:
            批处理对象
        """
        batch_id = f"batch-{uuid.uuid4().hex}"
        created_at = int(datetime.now().timestamp())
        
        # 创建批处理对象
        batch_obj = {
            "id": batch_id,
            "object": "batch",
            "endpoint": endpoint,
            "errors": None,
            "input_file_id": input_file_id,
            "completion_window": completion_window,
            "status": "validating_files",  # validating_files, in_progress, completed, failed
            "output_file_id": None,
            "error_file_id": None,
            "created_at": created_at,
            "in_progress_at": None,
            "expires_at": created_at + 86400,  # 24 小时后过期
            "finalizing_at": None,
            "completed_at": None,
            "failed_at": None,
            "expired_at": None,
            "cancelling_at": None,
            "cancelled_at": None,
            "request_counts": {
                "total": 0,
                "completed": 0,
                "failed": 0
            },
            "metadata": metadata or {}
        }
        
        # 保存元数据
        self.batches[batch_id] = batch_obj
        self._save_metadata()
        
        print(f"[BatchManager] Batch created: {batch_id}, input_file={input_file_id}")
        return batch_obj
    
    def get_batch(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """获取批处理信息"""
        return self.batches.get(batch_id)
    
    def list_batches(self, limit: int = 20, after: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        列出批处理
        
        Args:
            limit: 限制数量
            after: 分页游标
            
        Returns:
            批处理列表
        """
        batches = list(self.batches.values())
        
        # 按创建时间排序
        batches.sort(key=lambda x: x.get("created_at", 0), reverse=True)
        
        # 分页
        if after:
            try:
                start_index = next(
                    i for i, b in enumerate(batches) 
                    if b["id"] == after
                ) + 1
                batches = batches[start_index:]
            except (StopIteration, KeyError):
                pass
        
        return batches[:limit]
    
    def cancel_batch(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """
        取消批处理
        
        Returns:
            批处理对象
        """
        if batch_id not in self.batches:
            return None
        
        batch = self.batches[batch_id]
        
        # 更新状态
        cancelled_at = int(datetime.now().timestamp())
        batch["status"] = "cancelling"
        batch["cancelling_at"] = cancelled_at
        batch["cancelled_at"] = cancelled_at
        
        self._save_metadata()
        
        print(f"[BatchManager] Batch cancelled: {batch_id}")
        return batch
    
    def update_batch_status(
        self,
        batch_id: str,
        status: str,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        更新批处理状态
        
        Args:
            batch_id: 批处理 ID
            status: 新状态
            **kwargs: 其他要更新的字段
            
        Returns:
            批处理对象
        """
        if batch_id not in self.batches:
            return None
        
        batch = self.batches[batch_id]
        batch["status"] = status
        
        # 更新时间戳
        timestamp = int(datetime.now().timestamp())
        
        if status == "in_progress":
            batch["in_progress_at"] = timestamp
        elif status == "completed":
            batch["completed_at"] = timestamp
        elif status == "failed":
            batch["failed_at"] = timestamp
        elif status == "expired":
            batch["expired_at"] = timestamp
        
        # 更新其他字段
        for key, value in kwargs.items():
            batch[key] = value
        
        self._save_metadata()
        
        return batch


# 全局实例
_batch_manager: Optional[BatchManager] = None


def get_batch_manager() -> BatchManager:
    """获取批处理管理器"""
    global _batch_manager
    if _batch_manager is None:
        _batch_manager = BatchManager()
    return _batch_manager
