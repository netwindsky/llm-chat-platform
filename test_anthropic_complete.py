import requests
import json
import sys

# 测试配置
BASE_URL = "http://localhost:38520"
MODEL = "claude-3-sonnet-20240229"

def test_case(name, payload, expected_status=200):
    """测试单个用例"""
    url = f"{BASE_URL}/v1/messages"
    print(f"\n{'='*60}")
    print(f"测试: {name}")
    print(f"{'='*60}")
    print(f"请求: {json.dumps(payload, indent=2, ensure_ascii=False)[:500]}...")
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        print(f"\n状态码: {response.status_code}")
        
        if response.status_code == expected_status:
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
            return True
        else:
            print(f"❌ 失败 - 期望状态码 {expected_status}, 实际 {response.status_code}")
            print(f"响应: {response.text[:500]}")
            return False
    except Exception as e:
        print(f"❌ 异常: {e}")
        return False

# 测试用例列表
test_cases = [
    # 1. 基本文本请求
    ("基本文本请求", {
        "model": MODEL,
        "max_tokens": 100,
        "messages": [{"role": "user", "content": "Hello"}]
    }),
    
    # 2. 带 system 的请求
    ("带 system 的请求", {
        "model": MODEL,
        "max_tokens": 100,
        "system": "你是一个有帮助的助手",
        "messages": [{"role": "user", "content": "Hello"}]
    }),
    
    # 3. 多轮对话
    ("多轮对话", {
        "model": MODEL,
        "max_tokens": 100,
        "messages": [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好！有什么可以帮助你的吗？"},
            {"role": "user", "content": "谢谢"}
        ]
    }),
    
    # 4. content 为数组格式（单个 text）
    ("content 数组-单 text", {
        "model": MODEL,
        "max_tokens": 100,
        "messages": [{"role": "user", "content": [{"type": "text", "text": "Hello"}]}]
    }),
    
    # 5. content 为数组格式（多个 text）
    ("content 数组-多 text", {
        "model": MODEL,
        "max_tokens": 100,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": "Hello"},
            {"type": "text", "text": "World"}
        ]}]
    }),
    
    # 6. content 带 cache_control
    ("content 带 cache_control", {
        "model": MODEL,
        "max_tokens": 100,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": "Hello"},
            {"type": "text", "text": "World", "cache_control": {"type": "ephemeral"}}
        ]}]
    }),
    
    # 7. 带 tools 的请求
    ("带 tools 的请求", {
        "model": MODEL,
        "max_tokens": 100,
        "messages": [{"role": "user", "content": "列出当前目录"}],
        "tools": [{
            "name": "Bash",
            "description": "执行bash命令",
            "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}
        }]
    }),
    
    # 8. 带 tools 和 cache_control
    ("带 tools 和 cache_control", {
        "model": MODEL,
        "max_tokens": 100,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": "列出当前目录"},
            {"type": "text", "text": "使用 bash", "cache_control": {"type": "ephemeral"}}
        ]}],
        "tools": [{
            "name": "Bash",
            "description": "执行bash命令",
            "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}
        }]
    }),
    
    # 9. 流式请求
    ("流式请求", {
        "model": MODEL,
        "max_tokens": 100,
        "messages": [{"role": "user", "content": "Hello"}],
        "stream": True
    }),
    
    # 10. 带 temperature
    ("带 temperature", {
        "model": MODEL,
        "max_tokens": 100,
        "temperature": 0.5,
        "messages": [{"role": "user", "content": "Hello"}]
    }),
    
    # 11. 带 top_p
    ("带 top_p", {
        "model": MODEL,
        "max_tokens": 100,
        "top_p": 0.9,
        "messages": [{"role": "user", "content": "Hello"}]
    }),
    
    # 12. 带 stop_sequences
    ("带 stop_sequences", {
        "model": MODEL,
        "max_tokens": 100,
        "stop_sequences": ["stop"],
        "messages": [{"role": "user", "content": "Hello"}]
    }),
]

# 执行测试
print(f"开始测试 Anthropic API")
print(f"基础 URL: {BASE_URL}")
print(f"模型: {MODEL}")
print(f"测试用例数: {len(test_cases)}")

passed = 0
failed = 0

for name, payload in test_cases:
    if test_case(name, payload):
        passed += 1
    else:
        failed += 1

print(f"\n{'='*60}")
print(f"测试结果汇总")
print(f"{'='*60}")
print(f"通过: {passed}/{len(test_cases)}")
print(f"失败: {failed}/{len(test_cases)}")

if failed == 0:
    print("✅ 所有测试通过！")
else:
    print("❌ 存在失败的测试")
    sys.exit(1)
