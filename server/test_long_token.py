"""
Token超限测试脚本
测试场景：
1. 加载qwen3.5-122b-a10b-thinking-general模型，发送超过2048 token的请求
2. 切换到qwen3.5-122b-a10b-instruct-reasoning模型，发送超过2048 token的请求
3. 检查是否出现Token超出的异常
"""

import requests
import time
import json
import sys

BASE_URL = "http://127.0.0.1:38520"
API_BASE = f"{BASE_URL}/api/v1"

def generate_long_text(num_tokens=2500):
    """生成指定token数的文本（约4个字符=1个token）"""
    words = [
        "在", "这个", "漫长", "的", "宇宙", "中", "我们", "人类", "一直在", "探索",
        "未知", "的", "领域", "从", "最初", "的", "火", "到", "如今", "的",
        "人工智能", "我们", "不断", "进步", "科技", "发展", "日新月异", "世界",
        "变化", "越来越快", "信息", "时代", "数据", "成为", "新的", "石油",
        "算法", "成为", "新的", "力量", "机器", "学习", "深度", "神经网络",
        "大语言", "模型", "知识", "图谱", "强化", "学习", "迁移", "学习",
        "计算机", "视觉", "自然语言", "处理", "语音识别", "知识", "推理",
        "人工", "通用", "智能", "量子", "计算", "区块链", "元宇宙", "虚拟现实",
        "增强", "现实", "物联网", "5G", "6G", "通信", "卫星", "导航",
        "自动驾驶", "无人机", "机器人", "3D打印", "生物", "技术", "基因编辑",
        "新能源", "核聚变", "太阳能", "风能", "潮汐", "地热", "氢能",
        "航天", "火箭", "卫星", "空间站", "月球", "火星", "小行星", "彗星",
        "宇宙", "探索", "黑洞", "暗物质", "暗能量", "引力波", "相对论", "量子力学",
        "弦理论", "多维", "空间", "平行", "宇宙", "时间", "旅行", "未来",
        "过去", "现在", "永恒", "瞬间", "无限", "有限", "宇宙", "法则"
    ]
    repeat_times = (num_tokens // 4) + 1
    text = " ".join(words * repeat_times)
    return text[:num_tokens * 4]

def check_server():
    """检查服务器是否运行"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ 服务器运行正常，加载模型数: {data.get('models_loaded', 0)}")
            return True
    except Exception as e:
        print(f"✗ 服务器未运行: {e}")
        return False
    return False

def get_loaded_models():
    """获取已加载的模型列表"""
    try:
        response = requests.get(f"{API_BASE}/models/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return [m["id"] for m in data.get("models", []) if m.get("status") == "loaded"]
    except:
        pass
    return []

def load_model(model_id):
    """加载指定模型"""
    print(f"\n正在加载模型: {model_id} ...")
    try:
        response = requests.post(
            f"{API_BASE}/models/{model_id}/load",
            timeout=600
        )
        result = response.json()
        print(f"加载响应: {json.dumps(result, ensure_ascii=False, indent=2)}")

        if response.status_code == 200:
            max_wait = 600
            start_time = time.time()
            while time.time() - start_time < max_wait:
                loaded = get_loaded_models()
                print(f"已加载模型: {loaded}")
                if model_id in loaded:
                    print(f"✓ 模型 {model_id} 加载成功!")
                    return True
                time.sleep(5)
            print(f"✗ 模型加载超时")
            return False
        else:
            print(f"✗ 模型加载失败: {result}")
            return False
    except Exception as e:
        print(f"✗ 加载模型出错: {e}")
        return False

def unload_model(model_id):
    """卸载指定模型"""
    print(f"\n正在卸载模型: {model_id} ...")
    try:
        response = requests.post(
            f"{API_BASE}/models/{model_id}/unload",
            timeout=60
        )
        result = response.json()
        print(f"卸载响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
        return True
    except Exception as e:
        print(f"✗ 卸载模型出错: {e}")
        return False

def send_chat_request(model_id, messages, max_tokens=8192, temperature=1.0):
    """发送聊天请求"""
    print(f"\n发送请求到模型: {model_id}")
    print(f"消息数量: {len(messages)}")

    total_chars = sum(len(m.get("content", "")) for m in messages)
    estimated_tokens = total_chars // 4
    print(f"输入字符数: {total_chars}, 估算token数: {estimated_tokens}")
    print(f"max_tokens: {max_tokens}, temperature: {temperature}")

    try:
        start_time = time.time()
        response = requests.post(
            f"{API_BASE}/chat/completions",
            json={
                "model": model_id,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": False
            },
            timeout=600
        )
        elapsed = time.time() - start_time

        print(f"请求耗时: {elapsed:.2f}秒")
        print(f"响应状态码: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            usage = result.get("usage", {})
            print(f"✓ 请求成功!")
            print(f"  prompt_tokens: {usage.get('prompt_tokens', 'N/A')}")
            print(f"  completion_tokens: {usage.get('completion_tokens', 'N/A')}")
            print(f"  total_tokens: {usage.get('total_tokens', 'N/A')}")

            if "choices" in result and len(result["choices"]) > 0:
                msg = result["choices"][0].get("message", {})
                content = msg.get("content", "")
                thinking = msg.get("thinking", "")
                print(f"  回复长度: {len(content)} 字符")
                if thinking:
                    print(f"  思考长度: {len(thinking)} 字符")
            return {"success": True, "result": result}
        else:
            error = response.json() if response.text else {}
            print(f"✗ 请求失败: {json.dumps(error, ensure_ascii=False, indent=2)}")
            return {"success": False, "error": error, "status_code": response.status_code}

    except requests.exceptions.Timeout:
        print(f"✗ 请求超时!")
        return {"success": False, "error": "请求超时"}
    except Exception as e:
        print(f"✗ 请求出错: {e}")
        return {"success": False, "error": str(e)}

def test_model_long_prompt(model_id, prompt_tokens=2500):
    """测试模型处理长prompt"""
    print(f"\n{'='*60}")
    print(f"测试 {model_id} 处理超过2048 token的请求")
    print(f"{'='*60}")

    long_text = generate_long_text(prompt_tokens)
    print(f"生成了约 {prompt_tokens} token的输入文本 ({len(long_text)} 字符)")

    messages = [
        {"role": "system", "content": "你是一个有帮助的助手。"},
        {"role": "user", "content": f"请阅读以下内容，然后简单总结主要观点：\n\n{long_text}"}
    ]

    result = send_chat_request(model_id, messages, max_tokens=8192)
    return result

def main():
    print("="*60)
    print("Token超限测试开始")
    print("="*60)

    if not check_server():
        print("\n请先启动服务器: python main.py --port 38520")
        sys.exit(1)

    model1 = "qwen3.5-122b-a10b-thinking-general"
    model2 = "qwen3.5-122b-a10b-instruct-reasoning"

    print(f"\n\n{'#'*60}")
    print(f"# 测试1: 加载 {model1} 并发送超过2048 token的请求")
    print(f"{'#'*60}")

    if model1 not in get_loaded_models():
        if not load_model(model1):
            print(f"无法加载模型 {model1}")
            sys.exit(1)
    else:
        print(f"模型 {model1} 已经加载")

    print("\n--- 测试1a: 正常max_tokens测试 ---")
    result1a = test_model_long_prompt(model1, prompt_tokens=2500)
    time.sleep(2)

    print("\n--- 测试1b: 第二次测试 ---")
    result1b = test_model_long_prompt(model1, prompt_tokens=2500)
    time.sleep(2)

    print(f"\n\n{'#'*60}")
    print(f"# 测试2: 切换到 {model2} 并发送超过2048 token的请求")
    print(f"{'#'*60}")

    if model2 not in get_loaded_models():
        if not load_model(model2):
            print(f"无法加载模型 {model2}")
            sys.exit(1)
    else:
        print(f"模型 {model2} 已经加载")

    print("\n--- 测试2a: 切换后的第一次测试 ---")
    result2a = test_model_long_prompt(model2, prompt_tokens=2500)
    time.sleep(2)

    print("\n--- 测试2b: 切换后的第二次测试 ---")
    result2b = test_model_long_prompt(model2, prompt_tokens=2500)
    time.sleep(2)

    print("\n--- 测试2c: 更大token测试 (5000) ---")
    result2c = test_model_long_prompt(model2, prompt_tokens=5000)
    time.sleep(2)

    print("\n\n" + "="*60)
    print("测试总结")
    print("="*60)
    tests = [
        ("测试1a", model1, result1a),
        ("测试1b", model1, result1b),
        ("测试2a", model2, result2a),
        ("测试2b", model2, result2b),
        ("测试2c", model2, result2c),
    ]

    for name, model, result in tests:
        status = "✓ 成功" if result.get("success") else "✗ 失败"
        print(f"{name} ({model}): {status}")
        if not result.get("success"):
            print(f"  错误: {result.get('error')}")

    print("\n测试完成!")

if __name__ == "__main__":
    main()
