import sys
sys.path.insert(0, 'c:\\AI\\LLM')

from server.adapters.anthropic_adapter import AnthropicRequestConverter

# 测试 system message 转换
anthropic_body = {
    'model': 'claude-3-sonnet-20240229',
    'max_tokens': 100,
    'system': 'You are a helpful assistant',
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

print("Testing convert_request...")
openai_body = AnthropicRequestConverter.convert_request(anthropic_body)

print(f"\nOpenAI request messages:")
for i, msg in enumerate(openai_body.get('messages', [])):
    content = msg.get('content', '')
    print(f"  Message {i}: role={msg.get('role')}")
    print(f"    content type: {type(content).__name__}")
    if isinstance(content, list):
        print(f"    content length: {len(content)}")
        print(f"    content items: {content[:3]}...")  # 只显示前3个
    else:
        print(f"    content length: {len(str(content))}")
        print(f"    content preview: {str(content)[:200]}...")
