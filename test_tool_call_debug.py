import requests
import json

# 测试工具调用 - 查看模型实际返回什么
url = "http://localhost:38520/v1/messages"

payload = {
    "model": "claude-3-sonnet-20240229",
    "max_tokens": 200,
    "system": [
        {"type": "text", "text": "You are a helpful assistant"}
    ],
    "messages": [
        {"role": "user", "content": "当前目录文件有哪些？"}
    ],
    "tools": [
        {
            "name": "Glob",
            "description": "查找文件",
            "input_schema": {"type": "object", "properties": {"pattern": {"type": "string"}}, "required": ["pattern"]}
        },
        {
            "name": "Bash",
            "description": "执行bash命令",
            "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}
        }
    ]
}

print("发送工具调用请求...")
print(f"请求: {json.dumps(payload, indent=2, ensure_ascii=False)[:800]}...")

try:
    response = requests.post(url, json=payload, timeout=60)
    print(f"\n状态码: {response.status_code}")
    
    result = response.json()
    print(f"\n完整响应:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
except Exception as e:
    print(f"❌ 异常: {e}")
    import traceback
    print(traceback.format_exc())
