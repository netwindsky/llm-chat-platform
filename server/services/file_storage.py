"""
文件存储服务
用于管理 OpenAI Files API 的文件存储
"""

import os
import uuid
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

# 文件存储目录
STORAGE_DIR = Path("data/files")
METADATA_FILE = STORAGE_DIR / "metadata.json"


class FileStorage:
    """文件存储管理器"""
    
    def __init__(self):
        self.storage_dir = STORAGE_DIR
        self.metadata_file = METADATA_FILE
        self.files: Dict[str, Dict[str, Any]] = {}
        self._load_metadata()
    
    def _ensure_dirs(self):
        """确保存储目录存在"""
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        (self.storage_dir / "uploads").mkdir(exist_ok=True)
    
    def _load_metadata(self):
        """加载元数据"""
        self._ensure_dirs()
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, "r", encoding="utf-8") as f:
                    self.files = json.load(f)
            except Exception as e:
                print(f"[FileStorage] Failed to load metadata: {e}")
                self.files = {}
        else:
            self.files = {}
    
    def _save_metadata(self):
        """保存元数据"""
        self._ensure_dirs()
        try:
            with open(self.metadata_file, "w", encoding="utf-8") as f:
                json.dump(self.files, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[FileStorage] Failed to save metadata: {e}")
    
    def create_file(
        self,
        filename: str,
        purpose: str,
        content: bytes,
        content_type: str = "application/octet-stream"
    ) -> Dict[str, Any]:
        """
        创建文件
        
        Args:
            filename: 文件名
            purpose: 用途（fine-tune, batch 等）
            content: 文件内容
            content_type: MIME 类型
            
        Returns:
            文件对象
        """
        file_id = f"file-{uuid.uuid4().hex}"
        created_at = int(datetime.now().timestamp())
        
        # 保存文件
        file_path = self.storage_dir / "uploads" / f"{file_id}_{filename}"
        with open(file_path, "wb") as f:
            f.write(content)
        
        # 计算文件大小
        file_size = len(content)
        
        # 创建文件对象
        file_obj = {
            "id": file_id,
            "object": "file",
            "bytes": file_size,
            "created_at": created_at,
            "filename": filename,
            "purpose": purpose,
            "content_type": content_type,
            "status": "processed",
            "status_details": None
        }
        
        # 保存元数据
        self.files[file_id] = file_obj
        self._save_metadata()
        
        print(f"[FileStorage] File created: {file_id}, size={file_size}, purpose={purpose}")
        return file_obj
    
    def get_file(self, file_id: str) -> Optional[Dict[str, Any]]:
        """获取文件信息"""
        return self.files.get(file_id)
    
    def delete_file(self, file_id: str) -> bool:
        """
        删除文件
        
        Returns:
            是否删除成功
        """
        if file_id not in self.files:
            return False
        
        file_obj = self.files[file_id]
        filename = file_obj.get("filename", "")
        file_path = self.storage_dir / "uploads" / f"{file_id}_{filename}"
        
        # 删除物理文件
        if file_path.exists():
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"[FileStorage] Failed to delete physical file: {e}")
        
        # 删除元数据
        del self.files[file_id]
        self._save_metadata()
        
        print(f"[FileStorage] File deleted: {file_id}")
        return True
    
    def list_files(self, purpose: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        列出文件
        
        Args:
            purpose: 按用途过滤
            
        Returns:
            文件列表
        """
        if purpose:
            return [f for f in self.files.values() if f.get("purpose") == purpose]
        return list(self.files.values())
    
    def get_file_content(self, file_id: str) -> Optional[bytes]:
        """获取文件内容"""
        file_obj = self.files.get(file_id)
        if not file_obj:
            return None
        
        filename = file_obj.get("filename", "")
        file_path = self.storage_dir / "uploads" / f"{file_id}_{filename}"
        
        if file_path.exists():
            with open(file_path, "rb") as f:
                return f.read()
        return None


# 全局实例
_file_storage: Optional[FileStorage] = None


def get_file_storage() -> FileStorage:
    """获取文件存储实例"""
    global _file_storage
    if _file_storage is None:
        _file_storage = FileStorage()
    return _file_storage
