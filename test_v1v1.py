import requests
import json

# 测试 /v1/v1/messages 路径（Claude Code 使用的路径）
url = "http://localhost:38520/v1/v1/messages"

payload = {
    "model": "claude-3-sonnet-20240229",
    "max_tokens": 200,
    "system": [{"type": "text", "text": "You are a helpful assistant"}],
    "messages": [{"role": "user", "content": "当前目录有哪些文件？"}],
    "tools": [
        {
            "name": "Glob",
            "description": "查找文件",
            "input_schema": {"type": "object", "properties": {"pattern": {"type": "string"}}, "required": ["pattern"]}
        }
    ]
}

print(f"请求路径: {url}")
response = requests.post(url, json=payload, timeout=60)

print(f"状态码: {response.status_code}")
result = response.json()
print(f"\n响应内容:")
print(json.dumps(result, indent=2, ensure_ascii=False))
