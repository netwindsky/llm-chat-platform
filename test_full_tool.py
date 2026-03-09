import requests
import json

url = "http://localhost:38520/v1/v1/messages"

# 第一次请求 - 触发工具调用
print("=" * 50)
print("第一次请求 - 触发工具调用")
print("=" * 50)

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
print(f"content: {json.dumps(result.get('content'), indent=2, ensure_ascii=False)}")

# 检查是否有工具调用
if result.get('stop_reason') == 'tool_use':
    tool_call = result['content'][0]
    tool_name = tool_call['name']
    tool_input = tool_call['input']
    tool_id = tool_call['id']
    
    print(f"\n检测到工具调用：{tool_name}")
    print(f"工具输入：{tool_input}")
    
    # 模拟工具执行结果
    tool_result = ["file1.py", "file2.py", "test.py"]
    
    # 第二次请求 - 发送工具结果
    print("\n" + "=" * 50)
    print("第二次请求 - 发送工具结果")
    print("=" * 50)
    
    messages = [
        {"role": "user", "content": "当前目录有哪些文件？"},
        {
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "id": tool_id,
                    "name": tool_name,
                    "input": tool_input
                }
            ]
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": json.dumps(tool_result)
                }
            ]
        }
    ]
    
    payload2 = {
        "model": "claude-3-sonnet-20240229",
        "max_tokens": 500,
        "system": [{"type": "text", "text": "You are a helpful assistant."}],
        "messages": messages
    }
    
    response2 = requests.post(url, json=payload2, timeout=120)
    result2 = response2.json()
    
    print(f"状态码：{response2.status_code}")
    print(f"stop_reason: {result2.get('stop_reason')}")
    print(f"content: {json.dumps(result2.get('content'), indent=2, ensure_ascii=False)}")
else:
    print("\n没有检测到工具调用")
