import requests
import json

# 测试 system 为列表格式（不带 tools）
url = "http://localhost:38520/v1/messages"

payload = {
    "model": "claude-3-sonnet-20240229",
    "max_tokens": 100,
    "system": [
        {"type": "text", "text": "You are a helpful assistant"},
        {"type": "text", "text": "Be concise", "cache_control": {"type": "ephemeral"}}
    ],
    "messages": [
        {"role": "user", "content": "Hello, who are you?"}
    ]
}

print("Testing system as list format (no tools)...")

try:
    response = requests.post(url, json=payload, timeout=30)
    print(f"状态码: {response.status_code}")
    
    result = response.json()
    print(f"\n完整响应:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
except Exception as e:
    print(f"❌ 异常: {e}")
