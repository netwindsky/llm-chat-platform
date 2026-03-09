import requests
import json

url = "http://localhost:38520/v1/v1/messages"

payload = {
    "model": "qwen3.5-27b-instruct-reasoning",
    "max_tokens": 500,
    "system": [{"type": "text", "text": "You are a helpful assistant."}],
    "messages": [
        {"role": "user", "content": "当前目录有哪些文件？"}
    ],
    "tools": [
        {
            "name": "Glob",
            "description": "查找文件",
            "input_schema": {
                "type": "object",
                "properties": {"pattern": {"type": "string"}},
                "required": ["pattern"]
            }
        }
    ],
    "stream": True  # 测试流式
}

response = requests.post(url, json=payload, timeout=120, stream=True)

print(f"状态码：{response.status_code}")
print(f"Content-Type: {response.headers.get('content-type')}")

events = []
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
                events.append(event_type)
                
                if event_type == 'content_block_delta':
                    delta = event.get('delta', {})
                    text = delta.get('text', '')
                    full_content += text
                elif event_type == 'message_delta':
                    stop_reason = event.get('delta', {}).get('stop_reason')
                    print(f"\nmessage_delta: stop_reason={stop_reason}")
            except Exception as e:
                print(f"解析错误：{e}, data={data[:100]}")

print(f"\n所有事件类型:")
for i, e in enumerate(events):
    print(f"  [{i}] {e}")

print(f"\n完整内容:\n{full_content}")
print(f"\n是否包含 tool_use: {('<tool_use>' in full_content) and ('</tool_use>' in full_content)}")
