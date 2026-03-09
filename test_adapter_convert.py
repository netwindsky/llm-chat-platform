import json
import sys
sys.path.insert(0, 'c:\\AI\\LLM')

from server.adapters.anthropic_adapter import AnthropicRequestConverter
from server.core.backend import ChatMessage

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

print("Testing convert_messages...")
try:
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

    print("\nTesting ChatMessage conversion...")
    chat_messages = []
    for msg_dict in messages:
        msg = ChatMessage(
            role=msg_dict.get("role", "user"),
            content=msg_dict.get("content", "")
        )
        chat_messages.append(msg)
    print(f"Converted {len(chat_messages)} messages to ChatMessage objects")
    for i, msg in enumerate(chat_messages):
        print(f"  ChatMessage {i}: role={msg.role}, content type={type(msg.content).__name__}")

except Exception as e:
    import traceback
    print(f"Error: {e}")
    print(f"Traceback: {traceback.format_exc()}")
