"""
Anthropic API 适配器模块
将 Anthropic API 请求转换为 OpenAI API 请求
"""

from .anthropic_adapter import AnthropicAdapter
from .model_mapping import map_anthropic_to_openai_model

__all__ = ['AnthropicAdapter', 'map_anthropic_to_openai_model']
