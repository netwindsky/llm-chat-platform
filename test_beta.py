import requests
import json

# 模拟 Claude Code 发送的完整请求
# 包括 beta 参数（Claude Code 可能使用的）
url = "http://localhost:38520/v1/v1/messages?beta=true"

payload = {
    "model": "claude-3-sonnet-20240229",
    "max_tokens": 200,
    "system": [
        {"type": "text", "text": "You are a helpful assistant."},
        {"type": "text", "text": "This session has been running since March 9, 2025 at 11:15:35 AM UTC.", "cache_control": {"type": "ephemeral"}}
    ],
    "messages": [
        {"role": "user", "content": "当前目录文件有哪些？"}
    ],
    "tools": [
        {"name": "Glob", "description": "查找文件", "input_schema": {"type": "object", "properties": {"pattern": {"type": "string"}}, "required": ["pattern"]}},
        {"name": "Bash", "description": "执行命令", "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},
    ]
}

print(f"URL: {url}")
print(f"Payload: {json.dumps(payload, indent=2, ensure_ascii=False)[:500]}...")

response = requests.post(url, json=payload, timeout=60)

print(f"\n状态码: {response.status_code}")
print(f"响应头: {response.headers.get('content-type')}")
result = response.json()
print(f"\n响应:")
print(json.dumps(result, indent=2, ensure_ascii=False))
