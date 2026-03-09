import requests
import json

# 测试 Anthropic API - 工具调用
url = "http://localhost:38520/v1/messages"

payload = {
    "model": "claude-3-sonnet-20240229",
    "max_tokens": 100,
    "messages": [
        {
            "role": "user",
            "content": "列出当前目录的文件"
        }
    ],
    "tools": [
        {
            "name": "Bash",
            "description": "执行bash命令",
            "input_schema": {
                "type": "object",
                "properties": {
                    "command": {"type": "string"}
                },
                "required": ["command"]
            }
        }
    ]
}

print("Testing tool calling...")
print(f"URL: {url}")
print(f"Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")

try:
    response = requests.post(url, json=payload, timeout=30)
    print(f"\nStatus Code: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
    
    # 检查是否返回了 tool_use
    content = result.get("content", [])
    for item in content:
        if item.get("type") == "tool_use":
            print(f"\n✅ Tool use detected!")
            print(f"   Tool name: {item.get('name')}")
            print(f"   Tool input: {item.get('input')}")
        elif item.get("type") == "text":
            print(f"\n📝 Text response: {item.get('text', '')[:100]}...")
except Exception as e:
    print(f"Error: {e}")
