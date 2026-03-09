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
    "stream": False  # 测试非流式
}

response = requests.post(url, json=payload, timeout=120)
result = response.json()

print(f"状态码：{response.status_code}")
print(f"stop_reason: {result.get('stop_reason')}")
print(f"\n完整响应:")
print(json.dumps(result, indent=2, ensure_ascii=False))

# 检查 content 数组格式
if result.get('content'):
    print(f"\nContent 数组长度：{len(result['content'])}")
    for i, item in enumerate(result['content']):
        print(f"  [{i}] type={item.get('type')}")
        if item.get('type') == 'tool_use':
            print(f"      name={item.get('name')}, id={item.get('id')}, input={item.get('input')}")
