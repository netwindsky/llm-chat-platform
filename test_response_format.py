import requests
import json

url = "http://localhost:38520/v1/messages"

payload = {
    "model": "claude-3-sonnet-20240229",
    "max_tokens": 200,
    "system": [{"type": "text", "text": "You are a helpful assistant"}],
    "messages": [{"role": "user", "content": "当前目录文件有哪些？"}],
    "tools": [
        {
            "name": "Glob",
            "description": "查找文件",
            "input_schema": {"type": "object", "properties": {"pattern": {"type": "string"}}, "required": ["pattern"]}
        }
    ]
}

response = requests.post(url, json=payload, timeout=60)
result = response.json()

print("响应格式检查:")
print(f"  type: {result.get('type')}")
print(f"  role: {result.get('role')}")
print(f"  stop_reason: {result.get('stop_reason')}")
print(f"  content: {json.dumps(result.get('content'), indent=2, ensure_ascii=False)}")
