"""
Anthropic 模型到 OpenAI/本地模型的映射
"""

# Anthropic 模型名到本地模型名的映射
ANTHROPIC_TO_OPENAI_MODEL_MAP = {
    # Claude 3 Opus - 最强模型
    "claude-3-opus-20240229": "qwen3.5-35b-a3b-ud-q4-xl",
    "claude-3-opus-latest": "qwen3.5-35b-a3b-ud-q4-xl",

    # Claude 3.5 Sonnet - 最新版本
    "claude-3-5-sonnet-20241022": "qwen3.5-27b-ud-q4-xl-1-thinking-coding",
    "claude-3-5-sonnet-latest": "qwen3.5-27b-ud-q4-xl-1-thinking-coding",

    # Claude 3.5 Sonnet - 旧版本
    "claude-3-5-sonnet-20240620": "qwen3.5-27b-ud-q4-xl-1-thinking-general",

    # Claude 3 Sonnet
    "claude-3-sonnet-20240229": "qwen3.5-27b-ud-q4-xl-1",
    "claude-3-sonnet-latest": "qwen3.5-27b-ud-q4-xl-1",

    # Claude 3 Haiku - 快速模型
    "claude-3-haiku-20240307": "qwen3.5-9b-ud-q4",
    "claude-3-haiku-latest": "qwen3.5-9b-ud-q4",

    # 视觉模型
    "claude-3-opus-vision": "qwen3.5-35b-a3b-ud-q4-xl-vision",
    "claude-3-sonnet-vision": "qwen3.5-27b-vl",
    "claude-3-haiku-vision": "qwen3.5-9b-ud-q4-vision",

    # 代码模型
    "claude-3-5-sonnet-coding": "qwen3.5-27b-ud-q4-xl-1-thinking-coding",
}

# 反向映射（用于响应）
OPENAI_TO_ANTHROPIC_MODEL_MAP = {v: k for k, v in ANTHROPIC_TO_OPENAI_MODEL_MAP.items()}


def map_anthropic_to_openai_model(anthropic_model: str) -> str:
    """
    将 Anthropic 模型名映射到本地模型名

    Args:
        anthropic_model: Anthropic 模型名，如 "claude-3-sonnet-20240229"

    Returns:
        本地模型名，如 "qwen3.5-27b-ud-q4-xl-1"
    """
    return ANTHROPIC_TO_OPENAI_MODEL_MAP.get(anthropic_model, "qwen3.5-27b-ud-q4-xl-1")


def map_openai_to_anthropic_model(openai_model: str) -> str:
    """
    将本地模型名映射回 Anthropic 模型名

    Args:
        openai_model: 本地模型名

    Returns:
        Anthropic 模型名
    """
    return OPENAI_TO_ANTHROPIC_MODEL_MAP.get(openai_model, "claude-3-sonnet-20240229")


def get_default_anthropic_model() -> str:
    """获取默认的 Anthropic 模型名"""
    return "claude-3-sonnet-20240229"


def list_supported_anthropic_models() -> list:
    """列出所有支持的 Anthropic 模型"""
    return list(ANTHROPIC_TO_OPENAI_MODEL_MAP.keys())
