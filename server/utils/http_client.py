"""
HTTP客户端管理模块
统一管理所有网络访问，禁用代理以确保直连
"""

from typing import Optional


class HttpClient:
    """HTTP客户端管理类 - 统一管理所有网络访问，禁用代理"""
    
    @staticmethod
    def create_client(timeout: Optional[float] = None):
        """创建httpx客户端，禁用所有代理
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            httpx.AsyncClient: 配置好的异步HTTP客户端
        """
        import httpx
        
        if timeout:
            return httpx.AsyncClient(
                proxy=None, 
                trust_env=False,
                timeout=httpx.Timeout(timeout)
            )
        return httpx.AsyncClient(proxy=None, trust_env=False)
    
    @staticmethod
    def create_stream_client(timeout: Optional[float] = None):
        """创建支持流式传输的httpx客户端
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            httpx.AsyncClient: 配置好的异步HTTP客户端（支持流式）
        """
        import httpx
        
        if timeout:
            return httpx.AsyncClient(
                proxy=None, 
                trust_env=False,
                timeout=httpx.Timeout(timeout)
            )
        return httpx.AsyncClient(proxy=None, trust_env=False)
