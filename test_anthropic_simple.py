import requests
import json

# 测试 Anthropic API - 简化版本
url = "http://127.0.0.1:38520/v1/messages"

payload = {
    "model": "claude-3-sonnet-20240229",
    "max_tokens": 100,
    "messages": [
        {
            "role": "user",
            "content": "Hello World"  # 简化：直接使用字符串
        }
    ]
}

print("Sending request to Anthropic API...")
print(f"URL: {url}")
print(f"Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")

try:
    response = requests.post(url, json=payload, timeout=30)
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
except Exception as e:
    print(f"Error: {e}")
