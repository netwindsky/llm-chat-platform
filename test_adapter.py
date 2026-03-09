import json
import sys
sys.path.insert(0, 'c:\\AI\\LLM')

from server.adapters.anthropic_adapter import AnthropicRequestConverter

# 模拟 Claude Code 发送的消息
anthropic_body = {
    'model': 'claude-3-sonnet-20240229',
    'messages': [{
        'role': 'user',
        'content': [
            {'type': 'text', 'text': 'Hello'},
            {'type': 'text', 'text': 'World', 'cache_control': {'type': 'ephemeral'}}
        ]
    }],
    'tools': [{
        'name': 'Bash',
        'description': '执行bash命令',
        'input_schema': {'type': 'object', 'properties': {'command': {'type': 'string'}}, 'required': ['command']}
    }]
}

# 转换消息
messages = AnthropicRequestConverter.convert_messages(
    anthropic_body['messages'],
    None,
    anthropic_body['tools']
)

print('转换后的 messages:')
for i, msg in enumerate(messages):
    print(f'  Message {i}: role={msg["role"]}, content type={type(msg["content"]).__name__}')
    if isinstance(msg['content'], list):
        print(f'    content items: {msg["content"]}')
    else:
        print(f'    content: {msg["content"][:200]}...')
