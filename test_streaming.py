import requests
import json

# 测试流式响应
url = "http://localhost:38520/v1/messages"

payload = {
    "model": "claude-3-sonnet-20240229",
    "max_tokens": 50,
    "messages": [{"role": "user", "content": "Hello"}],
    "stream": True
}

print("测试流式响应...")
print(f"请求: {json.dumps(payload, indent=2, ensure_ascii=False)}")

try:
    response = requests.post(url, json=payload, timeout=30, stream=True)
    print(f"\n状态码: {response.status_code}")
    print(f"Content-Type: {response.headers.get('content-type')}")
    
    if response.status_code == 200:
        print("\n✅ 流式响应开始:")
        line_count = 0
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    data = line_str[6:]
                    if data == '[DONE]':
                        print("\n✅ 流式响应完成 [DONE]")
                        break
                    try:
                        event_data = json.loads(data)
                        event_type = event_data.get('type')
                        if event_type == 'message_start':
                            print(f"  事件: message_start, id={event_data.get('message', {}).get('id')}")
                        elif event_type == 'content_block_start':
                            print(f"  事件: content_block_start, index={event_data.get('index')}")
                        elif event_type == 'content_block_delta':
                            delta = event_data.get('delta', {})
                            if delta.get('type') == 'text_delta':
                                text = delta.get('text', '')
                                if line_count < 5:
                                    print(f"  事件: content_block_delta, text={text[:30]}...")
                                elif line_count == 5:
                                    print("  ...")
                                line_count += 1
                        elif event_type == 'content_block_stop':
                            print(f"  事件: content_block_stop, index={event_data.get('index')}")
                        elif event_type == 'message_delta':
                            print(f"  事件: message_delta, stop_reason={event_data.get('delta', {}).get('stop_reason')}")
                        elif event_type == 'message_stop':
                            print(f"  事件: message_stop")
                    except json.JSONDecodeError:
                        print(f"  原始数据: {data[:100]}")
        print("\n✅ 流式响应测试通过!")
    else:
        print(f"❌ 失败 - 状态码 {response.status_code}")
        print(f"响应: {response.text[:500]}")
except Exception as e:
    print(f"❌ 异常: {e}")
    import traceback
    print(traceback.format_exc())
