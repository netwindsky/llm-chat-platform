import requests
import json

url = "http://localhost:38520/v1/v1/messages"

payload = {
    "model": "claude-3-sonnet-20240229",
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
    ]
}

response = requests.post(url, json=payload, timeout=120)
result = response.json()

print(f"状态码：{response.status_code}")
print(f"stop_reason: {result.get('stop_reason')}")
print(f"\n完整 content:")
print(json.dumps(result.get('content'), indent=2, ensure_ascii=False))

# 检查是否有工具调用
if result.get('stop_reason') == 'tool_use':
    print("\n✓ 检测到工具调用！")
    if result['content'][0].get('type') == 'tool_use':
        tool_call = result['content'][0]
        print(f"  工具名：{tool_call['name']}")
        print(f"  工具 ID: {tool_call['id']}")
        print(f"  输入：{tool_call['input']}")
else:
    print("\n✗ 没有检测到工具调用")
