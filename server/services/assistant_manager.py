"""
Assistant API 服务
用于管理 OpenAI Assistant API 的助手、线程和消息
"""

import uuid
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

# Assistant 存储目录
ASSISTANTS_DIR = Path("data/assistants")
METADATA_FILE = ASSISTANTS_DIR / "metadata.json"


class AssistantManager:
    """Assistant 管理器"""
    
    def __init__(self):
        self.assistants_dir = ASSISTANTS_DIR
        self.metadata_file = METADATA_FILE
        self.assistants: Dict[str, Dict[str, Any]] = {}
        self.threads: Dict[str, Dict[str, Any]] = {}
        self.messages: Dict[str, List[Dict[str, Any]]] = {}  # thread_id -> messages
        self.runs: Dict[str, Dict[str, Any]] = {}  # run_id -> run
        self._load_metadata()
    
    def _ensure_dirs(self):
        """确保存储目录存在"""
        self.assistants_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_metadata(self):
        """加载元数据"""
        self._ensure_dirs()
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.assistants = data.get("assistants", {})
                    self.threads = data.get("threads", {})
                    self.messages = data.get("messages", {})
                    self.runs = data.get("runs", {})
            except Exception as e:
                print(f"[AssistantManager] Failed to load metadata: {e}")
                self.assistants = {}
                self.threads = {}
                self.messages = {}
                self.runs = {}
        else:
            self.assistants = {}
            self.threads = {}
            self.messages = {}
            self.runs = {}
    
    def _save_metadata(self):
        """保存元数据"""
        self._ensure_dirs()
        try:
            with open(self.metadata_file, "w", encoding="utf-8") as f:
                json.dump({
                    "assistants": self.assistants,
                    "threads": self.threads,
                    "messages": self.messages,
                    "runs": self.runs
                }, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[AssistantManager] Failed to save metadata: {e}")
    
    # ==================== Assistant 管理 ====================
    
    def create_assistant(
        self,
        name: str,
        model: str,
        description: Optional[str] = None,
        instructions: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """创建助手"""
        assistant_id = f"asst-{uuid.uuid4().hex}"
        created_at = int(datetime.now().timestamp())
        
        assistant = {
            "id": assistant_id,
            "object": "assistant",
            "created_at": created_at,
            "name": name,
            "model": model,
            "description": description,
            "instructions": instructions,
            "tools": tools or [],
            "file_ids": [],
            "metadata": metadata or {}
        }
        
        self.assistants[assistant_id] = assistant
        self._save_metadata()
        
        print(f"[AssistantManager] Assistant created: {assistant_id}")
        return assistant
    
    def get_assistant(self, assistant_id: str) -> Optional[Dict[str, Any]]:
        """获取助手信息"""
        return self.assistants.get(assistant_id)
    
    def list_assistants(
        self,
        limit: int = 20,
        order: str = "desc",
        after: Optional[str] = None,
        before: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """列出助手"""
        assistants = list(self.assistants.values())
        
        # 排序
        assistants.sort(
            key=lambda x: x.get("created_at", 0),
            reverse=(order == "desc")
        )
        
        # 分页
        if after:
            try:
                start_index = next(
                    i for i, a in enumerate(assistants) 
                    if a["id"] == after
                ) + 1
                assistants = assistants[start_index:]
            except (StopIteration, KeyError):
                pass
        
        return assistants[:limit]
    
    def update_assistant(
        self,
        assistant_id: str,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """更新助手"""
        if assistant_id not in self.assistants:
            return None
        
        assistant = self.assistants[assistant_id]
        
        # 更新字段
        for key, value in kwargs.items():
            if key in ["name", "model", "description", "instructions", "tools", "metadata"]:
                assistant[key] = value
        
        self._save_metadata()
        return assistant
    
    def delete_assistant(self, assistant_id: str) -> bool:
        """删除助手"""
        if assistant_id not in self.assistants:
            return False
        
        del self.assistants[assistant_id]
        self._save_metadata()
        
        print(f"[AssistantManager] Assistant deleted: {assistant_id}")
        return True
    
    # ==================== Thread 管理 ====================
    
    def create_thread(
        self,
        messages: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """创建线程"""
        thread_id = f"thread-{uuid.uuid4().hex}"
        created_at = int(datetime.now().timestamp())
        
        thread = {
            "id": thread_id,
            "object": "thread",
            "created_at": created_at,
            "metadata": metadata or {}
        }
        
        self.threads[thread_id] = thread
        self.messages[thread_id] = []
        
        # 添加初始消息
        if messages:
            for msg in messages:
                self.add_message(thread_id, msg.get("role", "user"), msg.get("content", ""))
        
        self._save_metadata()
        
        print(f"[AssistantManager] Thread created: {thread_id}")
        return thread
    
    def get_thread(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """获取线程信息"""
        return self.threads.get(thread_id)
    
    def update_thread(
        self,
        thread_id: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> Optional[Dict[str, Any]]:
        """更新线程"""
        if thread_id not in self.threads:
            return None
        
        if metadata is not None:
            self.threads[thread_id]["metadata"] = metadata
            self._save_metadata()
        
        return self.threads[thread_id]
    
    def delete_thread(self, thread_id: str) -> bool:
        """删除线程"""
        if thread_id not in self.threads:
            return False
        
        del self.threads[thread_id]
        if thread_id in self.messages:
            del self.messages[thread_id]
        self._save_metadata()
        
        print(f"[AssistantManager] Thread deleted: {thread_id}")
        return True
    
    # ==================== Message 管理 ====================
    
    def add_message(
        self,
        thread_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """添加消息到线程"""
        if thread_id not in self.messages:
            self.messages[thread_id] = []
        
        message_id = f"msg-{uuid.uuid4().hex}"
        created_at = int(datetime.now().timestamp())
        
        message = {
            "id": message_id,
            "object": "thread.message",
            "created_at": created_at,
            "thread_id": thread_id,
            "role": role,
            "content": [
                {
                    "type": "text",
                    "text": {
                        "value": content,
                        "annotations": []
                    }
                }
            ],
            "metadata": metadata or {},
            "assistant_id": None,
            "run_id": None,
            "file_ids": []
        }
        
        self.messages[thread_id].append(message)
        self._save_metadata()
        
        print(f"[AssistantManager] Message added: {message_id} to thread {thread_id}")
        return message
    
    def get_message(self, thread_id: str, message_id: str) -> Optional[Dict[str, Any]]:
        """获取消息"""
        if thread_id not in self.messages:
            return None
        
        for msg in self.messages[thread_id]:
            if msg["id"] == message_id:
                return msg
        
        return None
    
    def list_messages(
        self,
        thread_id: str,
        limit: int = 20,
        order: str = "desc"
    ) -> List[Dict[str, Any]]:
        """列出线程中的消息"""
        if thread_id not in self.messages:
            return []
        
        messages = self.messages[thread_id].copy()
        
        # 排序
        messages.sort(
            key=lambda x: x.get("created_at", 0),
            reverse=(order == "desc")
        )
        
        return messages[:limit]
    
    # ==================== Run 管理 ====================
    
    def create_run(
        self,
        thread_id: str,
        assistant_id: str,
        instructions: Optional[str] = None,
        additional_instructions: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """创建运行"""
        run_id = f"run-{uuid.uuid4().hex}"
        created_at = int(datetime.now().timestamp())
        
        run = {
            "id": run_id,
            "object": "thread.run",
            "created_at": created_at,
            "assistant_id": assistant_id,
            "thread_id": thread_id,
            "status": "queued",  # queued, in_progress, requires_action, cancelling, cancelled, failed, completed, incomplete
            "instructions": instructions,
            "additional_instructions": additional_instructions,
            "tools": tools or [],
            "metadata": metadata or {},
            "last_error": None,
            "expires_at": created_at + 3600,  # 1 小时后过期
            "started_at": None,
            "completed_at": None,
            "cancelled_at": None,
            "failed_at": None,
            "required_action": None
        }
        
        self.runs[run_id] = run
        self._save_metadata()
        
        print(f"[AssistantManager] Run created: {run_id}")
        return run
    
    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """获取运行信息"""
        return self.runs.get(run_id)
    
    def list_runs(
        self,
        thread_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """列出线程中的运行"""
        runs = [r for r in self.runs.values() if r.get("thread_id") == thread_id]
        runs.sort(key=lambda x: x.get("created_at", 0), reverse=True)
        return runs[:limit]
    
    def cancel_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """取消运行"""
        if run_id not in self.runs:
            return None
        
        run = self.runs[run_id]
        cancelled_at = int(datetime.now().timestamp())
        
        run["status"] = "cancelled"
        run["cancelled_at"] = cancelled_at
        
        self._save_metadata()
        
        print(f"[AssistantManager] Run cancelled: {run_id}")
        return run
    
    def update_run_status(
        self,
        run_id: str,
        status: str,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """更新运行状态"""
        if run_id not in self.runs:
            return None
        
        run = self.runs[run_id]
        run["status"] = status
        
        timestamp = int(datetime.now().timestamp())
        
        if status == "in_progress":
            run["started_at"] = timestamp
        elif status == "completed":
            run["completed_at"] = timestamp
        elif status == "failed":
            run["failed_at"] = timestamp
            if "error" in kwargs:
                run["last_error"] = kwargs["error"]
        
        for key, value in kwargs.items():
            run[key] = value
        
        self._save_metadata()
        return run


# 全局实例
_assistant_manager: Optional[AssistantManager] = None


def get_assistant_manager() -> AssistantManager:
    """获取 Assistant 管理器"""
    global _assistant_manager
    if _assistant_manager is None:
        _assistant_manager = AssistantManager()
    return _assistant_manager
