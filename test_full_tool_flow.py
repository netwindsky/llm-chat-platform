import requests
import json

# 模拟完整的工具调用流程
url = "http://localhost:38520/v1/messages"

# 第一次请求：让模型生成工具调用
payload1 = {
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

print("=== 第一次请求 ===")
response1 = requests.post(url, json=payload1, timeout=60)
result1 = response1.json()
print(f"stop_reason: {result1.get('stop_reason')}")
print(f"content: {json.dumps(result1.get('content'), indent=2, ensure_ascii=False)}")

# 第二次请求：把工具结果发送回去
if result1.get('stop_reason') == 'tool_use' and result1.get('content'):
    tool_block = result1['content'][0]
    tool_name = tool_block.get('name')
    tool_input = tool_block.get('input')
    tool_id = tool_block.get('id')
    
    print(f"\n=== 工具调用 ===")
    print(f"工具名: {tool_name}")
    print(f"参数: {tool_input}")
    
    # 模拟执行工具
    if tool_name == "Glob":
        import glob as g
        files = g.glob(tool_input.get('pattern', '*'))
        tool_result = "\n".join(files)
    else:
        tool_result = "Unknown tool"
    
    print(f"执行结果: {tool_result}")
    
    # 发送工具结果给模型
    payload2 = {
        "model": "claude-3-sonnet-20240229",
        "max_tokens": 200,
        "system": [{"type": "text", "text": "You are a helpful assistant"}],
        "messages": [
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
                "role": "tool",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": tool_result
                    }
                ]
            }
        ],
        "tools": [
            {
                "name": "Glob",
                "description": "查找文件",
                "input_schema": {"type": "object", "properties": {"pattern": {"type": "string"}}, "required": ["pattern"]}
            }
        ]
    }
    
    print("\n=== 第二次请求（带工具结果）===")
    response2 = requests.post(url, json=payload2, timeout=60)
    result2 = response2.json()
    print(f"stop_reason: {result2.get('stop_reason')}")
    print(f"content: {json.dumps(result2.get('content'), indent=2, ensure_ascii=False)}")
