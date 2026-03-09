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
response = requests.post(url, json=payload, timeout=60, stream=True)

print(f"状态码: {response.status_code}")
print(f"Content-Type: {response.headers.get('content-type')}")

print("\n流式事件:")
for line in response.iter_lines():
    if line:
        line_str = line.decode('utf-8')
        if line_str.startswith('data: '):
            data = line_str[6:]
            if data == '[DONE]':
                print("  [DONE]")
                break
            try:
                event = json.loads(data)
                event_type = event.get('type')
                if event_type == 'message_start':
                    print(f"  message_start: id={event.get('message', {}).get('id')}")
                elif event_type == 'content_block_start':
                    print(f"  content_block_start: index={event.get('index')}")
                elif event_type == 'content_block_delta':
                    delta = event.get('delta', {})
                    if delta.get('type') == 'text_delta':
                        text = delta.get('text', '')
                        print(f"  content_block_delta: text={text[:50]}...")
                elif event_type == 'content_block_stop':
                    print(f"  content_block_stop: index={event.get('index')}")
                elif event_type == 'message_delta':
                    print(f"  message_delta: stop_reason={event.get('delta', {}).get('stop_reason')}")
                elif event_type == 'message_stop':
                    print(f"  message_stop")
            except:
                print(f"  raw: {data[:100]}")
