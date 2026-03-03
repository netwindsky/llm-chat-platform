"""
直接测试 llama-server 原始 API
绕过后端处理，验证是模型能力问题还是后端处理问题
"""
import httpx
import json

LLAMA_SERVER_URL = "http://127.0.0.1:38521"

def test_chat_direct(messages, **kwargs):
    """直接调用 llama-server API"""
    payload = {
        "messages": messages,
        "temperature": kwargs.get("temperature", 0.7),
        "top_p": kwargs.get("top_p", 0.8),
        "max_tokens": kwargs.get("max_tokens", 4096),
        "stream": False
    }
    
    if kwargs.get("enable_thinking") is not None:
        payload["chat_template_kwargs"] = {"enable_thinking": kwargs["enable_thinking"]}
    
    print(f"\n{'='*60}")
    print("Request Payload:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"{'='*60}\n")
    
    with httpx.Client(timeout=300.0) as client:
        response = client.post(
            f"{LLAMA_SERVER_URL}/v1/chat/completions",
            json=payload
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"\n{'='*60}")
        print("Raw Response:")
        try:
            result = response.json()
            print(json.dumps(result, indent=2, ensure_ascii=False))
        except:
            print(response.text)
        print(f"{'='*60}\n")
        
        return response

def test_tool_calling():
    """测试工具调用能力"""
    
    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant with access to tools. When you need to use a tool, respond with a tool call in the correct format."
        },
        {
            "role": "user",
            "content": "What is the weather in Tokyo today? Use the get_weather tool."
        }
    ]
    
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get the current weather for a location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "City name"
                        }
                    },
                    "required": ["location"]
                }
            }
        }
    ]
    
    payload = {
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto",
        "temperature": 0.7,
        "max_tokens": 1024,
        "stream": False
    }
    
    print("\n" + "="*60)
    print("Testing Tool Calling Capability")
    print("="*60)
    print("\nRequest Payload:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    
    with httpx.Client(timeout=300.0) as client:
        response = client.post(
            f"{LLAMA_SERVER_URL}/v1/chat/completions",
            json=payload
        )
        
        print(f"\nStatus Code: {response.status_code}")
        print("\nResponse:")
        try:
            result = response.json()
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
            # Check for tool calls
            choices = result.get("choices", [])
            if choices:
                message = choices[0].get("message", {})
                if "tool_calls" in message:
                    print("\n✅ Model supports tool calling!")
                    print(f"Tool calls: {message['tool_calls']}")
                else:
                    print("\n❌ No tool_calls in response")
                    print(f"Content: {message.get('content', '')}")
        except Exception as e:
            print(f"Error parsing response: {e}")
            print(response.text)

def test_simple_chat():
    """测试简单对话"""
    messages = [
        {"role": "user", "content": "Hello, what is 2+2?"}
    ]
    return test_chat_direct(messages)

def test_task_prompt():
    """测试用户的 task prompt"""
    messages = [
        {
            "role": "user", 
            "content": """print(task(agent="explore", run_in_background=true, load_skills=["superpowers/brainstorming"], description="Analyze NWS Tools Chrome extension structure and functionality", prompt="I need to understand this Chrome extension's purpose, features, and architecture. Find: main entry points, module structure, features implemented, dependencies usage, configuration files. Focus on: manifest.json permissions, module organization, feature modules (translation, summary, image downloader), content scripts, background scripts, UI components. Skip node_modules. Return structured analysis of what this extension does and how it's organized."))"""
        }
    ]
    return test_chat_direct(messages, temperature=0.7)

if __name__ == "__main__":
    print("="*60)
    print("LLAMA-SERVER Direct API Test")
    print(f"Server: {LLAMA_SERVER_URL}")
    print("="*60)
    
    # Check health
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(f"{LLAMA_SERVER_URL}/health")
            print(f"\nHealth Check: {resp.status_code}")
            if resp.status_code == 200:
                print("✅ Server is running")
            else:
                print("❌ Server health check failed")
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        exit(1)
    
    print("\n" + "="*60)
    print("Select test:")
    print("1. Simple chat test")
    print("2. Tool calling test")
    print("3. Task prompt test")
    print("4. All tests")
    print("="*60)
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    if choice == "1":
        test_simple_chat()
    elif choice == "2":
        test_tool_calling()
    elif choice == "3":
        test_task_prompt()
    elif choice == "4":
        test_simple_chat()
        test_tool_calling()
        test_task_prompt()
    else:
        print("Invalid choice")
