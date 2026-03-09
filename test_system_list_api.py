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
print(f"请求: {json.dumps(payload, indent=2, ensure_ascii=False)[:500]}...")

try:
    response = requests.post(url, json=payload, timeout=30)
    print(f"\n状态码: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 成功")
        print(f"响应类型: {result.get('type')}")
        print(f"角色: {result.get('role')}")
        content = result.get('content', [])
        print(f"内容块数量: {len(content)}")
        for i, item in enumerate(content):
            print(f"  块 {i}: type={item.get('type')}")
            if item.get('type') == 'tool_use':
                print(f"    name: {item.get('name')}")
                print(f"    input: {item.get('input')}")
            elif item.get('type') == 'text':
                text = item.get('text', '')
                print(f"    text: {text[:100]}...")
    else:
        print(f"❌ 失败 - 状态码 {response.status_code}")
        print(f"响应: {response.text[:500]}")
except Exception as e:
    print(f"❌ 异常: {e}")
    import traceback
    print(traceback.format_exc())
