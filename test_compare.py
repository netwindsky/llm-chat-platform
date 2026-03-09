import requests
import json

# 同时请求两个接口，比较响应
url1 = "http://localhost:38520/api/v1/chat/completions"  # 我的 API
url2 = "http://localhost:38521/v1/chat/completions"       # llama-server 原生

data = {
    "model": "Qwen3.5-35B-A3B-UD-Q4_K_XL.gguf",
    "messages": [{"role": "user", "content": "你好"}],
    "stream": True,
    "temperature": 0.7
}

print("=== 测试 38521 (llama-server 原生) ===")
response2 = requests.post(url2, json=data, stream=True)
print(f"Status: {response2.status_code}")

chunk_count = 0
thinking_chunks = 0
for line in response2.iter_lines():
    if line:
        chunk_count += 1
        line_str = line.decode('utf-8')
        if line_str.startswith('data: ') and line_str != 'data: [DONE]':
            try:
                chunk = json.loads(line_str[6:])
                if 'choices' in chunk and len(chunk['choices']) > 0:
                    delta = chunk['choices'][0].get('delta', {})
                    if delta.get('reasoning_content'):
                        thinking_chunks += 1
                        if thinking_chunks <= 3:
                            print(f"Chunk {chunk_count}: reasoning_content = '{delta.get('reasoning_content')}'")
                    elif delta.get('thinking'):
                        thinking_chunks += 1
                        if thinking_chunks <= 3:
                            print(f"Chunk {chunk_count}: thinking = '{delta.get('thinking')}'")
            except Exception as e:
                print(f"Parse error: {e}")

print(f"\nTotal chunks with thinking/reasoning_content: {thinking_chunks}/{chunk_count}")
print(f"\n=== 38521 返回的字段名确认 ===")

# 重新请求，打印第一个有 thinking 内容的 chunk
response3 = requests.post(url2, json=data, stream=True)
for line in response3.iter_lines():
    if line:
        line_str = line.decode('utf-8')
        if line_str.startswith('data: ') and line_str != 'data: [DONE]':
            try:
                chunk = json.loads(line_str[6:])
                if 'choices' in chunk and len(chunk['choices']) > 0:
                    delta = chunk['choices'][0].get('delta', {})
                    if delta.get('reasoning_content') or delta.get('thinking'):
                        print(f"Delta keys: {list(delta.keys())}")
                        print(f"Full delta: {delta}")
                        break
            except:
                pass
