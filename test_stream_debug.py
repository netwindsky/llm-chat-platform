import requests
import json

url = "http://localhost:38520/v1/v1/messages"

payload = {
    "model": "claude-3-sonnet-20240229",
    "max_tokens": 200,
    "system": [{"type": "text", "text": "You are a helpful assistant"}],
    "messages": [{"role": "user", "content": "当前目录有哪些文件？"}],
    "tools": [
        {"name": "Glob", "description": "查找文件", "input_schema": {"type": "object", "properties": {"pattern": {"type": "string"}}, "required": ["pattern"]}}
    ],
    "stream": True
}

print("测试流式响应...")
response = requests.post(url, json=payload, timeout=120, stream=True)

print(f"状态码：{response.status_code}")

full_content = ""
for line in response.iter_lines():
    if line:
        line_str = line.decode('utf-8')
        if line_str.startswith('data: '):
            data = line_str[6:]
            if data == '[DONE]':
                break
            try:
                event = json.loads(data)
                event_type = event.get('type')
                if event_type == 'content_block_delta':
                    delta = event.get('delta', {})
                    text = delta.get('text', '')
                    full_content += text
                    print(f"  收到内容：{text}", end='')
                elif event_type == 'message_delta':
                    stop_reason = event.get('delta', {}).get('stop_reason')
                    print(f"\n\n  message_delta: stop_reason={stop_reason}")
            except Exception as e:
                print(f"  解析错误：{e}")

print(f"\n\n完整内容:\n{full_content}")
print(f"\n是否包含 tool_use 标签：{('<tool_use>' in full_content) and ('</tool_use>' in full_content)}")
