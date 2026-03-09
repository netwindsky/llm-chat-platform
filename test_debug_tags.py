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

print(f"stop_reason: {result.get('stop_reason')}")
text = result['content'][0]['text']
print(f"\n完整文本:\n{text}")
print(f"\n字符分析:")
for i, char in enumerate(text[:50]):
    print(f"  {i}: '{char}' (ord={ord(char)})")

print(f"\n是否包含 '<tool use>': {'<tool use>' in text}")
print(f"是否包含 '</tool use>': {'</tool use>' in text}")
print(f"是否包含 '<tool_use>': {'<tool_use>' in text}")
print(f"是否包含 '</tool_use>': {'</tool_use>' in text}")
print(f"是否包含 '<tool-use>': {'<tool-use>' in text}")
print(f"是否包含 '</tool-use>': {'</tool-use>' in text}")
