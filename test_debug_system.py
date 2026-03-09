import sys
sys.path.insert(0, 'c:\\AI\\LLM')

from server.adapters.anthropic_adapter import AnthropicRequestConverter
import json

# 测试 system 为列表格式的情况
anthropic_body = {
    'model': 'claude-3-sonnet-20240229',
    'max_tokens': 100,
    'system': [
        {'type': 'text', 'text': 'You are a helpful assistant'},
        {'type': 'text', 'text': 'Be concise', 'cache_control': {'type': 'ephemeral'}}
    ],
    'messages': [
        {
            'role': 'user',
            'content': 'Hello'
        }
    ],
    'tools': [
        {
            'name': 'Bash',
            'description': '执行bash命令',
            'input_schema': {'type': 'object', 'properties': {'command': {'type': 'string'}}, 'required': ['command']}
        }
    ]
}

print("Testing convert_request with system as list...")
openai_body = AnthropicRequestConverter.convert_request(anthropic_body)

print(f"\nOpenAI request:")
print(json.dumps(openai_body, indent=2, ensure_ascii=False))
