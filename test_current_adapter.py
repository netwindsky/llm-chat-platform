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

print("Testing convert_messages...")
messages = AnthropicRequestConverter.convert_messages(
    anthropic_body['messages'],
    anthropic_body['system'],
    anthropic_body['tools']
)

print(f"\nConverted messages:")
for i, msg in enumerate(messages):
    content = msg.get('content', '')
    print(f"  Message {i}: role={msg.get('role')}")
    print(f"    content type: {type(content).__name__}")
    if isinstance(content, list):
        print(f"    ERROR: content is list!")
        print(f"    content: {content[:3]}...")
    else:
        print(f"    content length: {len(str(content))}")
        print(f"    content is string: ✓")
