import requests
import json

# 测试 system 为列表格式
url = "http://localhost:38520/v1/messages"

payload = {
    "model": "claude-3-sonnet-20240229",
    "max_tokens": 100,
    "system": [
        {"type": "text", "text": "You are a helpful assistant"},
        {"type": "text", "text": "Be concise", "cache_control": {"type": "ephemeral"}}
    ],
    "messages": [
        {"role": "user", "content": "Hello"}
    ],
    "tools": [
        {
            "name": "Bash",
            "description": "执行bash命令",
            "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}
        }
    ]
}

print("Testing system as list format...")

try:
    response = requests.post(url, json=payload, timeout=30)
    print(f"状态码: {response.status_code}")
    
    result = response.json()
    print(f"\n完整响应:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
except Exception as e:
    print(f"❌ 异常: {e}")
    import traceback
    print(traceback.format_exc())
