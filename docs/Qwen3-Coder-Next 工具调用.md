Qwen3-Coder-Next 工具调用
在一个新终端中，我们创建一些工具，例如相加两个数字、执行 Python 代码、执行 Linux 功能等等：
import json, subprocess, random
from typing import Any
def add_number(a: float | str, b: float | str) -> float:
    return float(a) + float(b)
def multiply_number(a: float | str, b: float | str) -> float:
    return float(a) * float(b)
def substract_number(a: float | str, b: float | str) -> float:
    return float(a) - float(b)
def write_a_story() -> str:
    return random.choice([
        "很久以前，在一个遥远的星系……",
        "有两个朋友，他们喜欢树懒和代码……",
        "世界正在终结，因为每只树懒都进化出了超人的智慧……",
        "在一个朋友不知情的情况下，另一个人不小心写了一个能让树懒进化的程序……",
    ])
def terminal(command: str) -> str:
    if "rm" in command or "sudo" in command or "dd" in command or "chmod" in command:
        msg = "无法执行 'rm, sudo, dd, chmod' 命令，因为它们是危险的"
        print(msg); return msg
    print(f"正在执行终端命令 `{command}`")
    try:
        return str(subprocess.run(command, capture_output = True, text = True, shell = True, check = True).stdout)
    except subprocess.CalledProcessError as e:
        return f"命令失败：{e.stderr}"
def python(code: str) -> str:
    data = {}
    exec(code, data)
    del data["__builtins__"]
    return str(data)
MAP_FN = {
    "add_number": add_number,
    "multiply_number": multiply_number,
    "substract_number": substract_number,
    "write_a_story": write_a_story,
    "terminal": terminal,
    "python": python,
}
tools = [
    {
        "type": "function",
        "function": {
            "name": "add_number",
            "description": "对两个数字求和。",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {
                        "type": "string",
                        "description": "第一个数字。",
                    },
                    "b": {
                        "type": "string",
                        "description": "第二个数字。",
                    },
                },
                "required": ["a", "b"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "multiply_number",
            "description": "将两个数字相乘。",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {
                        "type": "string",
                        "description": "第一个数字。",
                    },
                    "b": {
                        "type": "string",
                        "description": "第二个数字。",
                    },
                },
                "required": ["a", "b"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "substract_number",
            "description": "对两个数字求差。",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {
                        "type": "string",
                        "description": "第一个数字。",
                    },
                    "b": {
                        "type": "string",
                        "description": "第二个数字。",
                    },
                },
                "required": ["a", "b"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_a_story",
            "description": "写一个随机故事。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "terminal",
            "description": "执行终端中的操作。",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "你希望启动的命令，例如 `ls`、`rm`，...",
                    },
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "python",
            "description": "使用一些将要运行的 Python 代码调用 Python 解释器。",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "要运行的 Python 代码",
                    },
                },
                "required": ["code"],
            },
        },
    },
]
然后我们使用下面的函数，这些函数会自动解析函数调用并为任何 LLM 调用 OpenAI 端点：
from openai import OpenAI
def unsloth_inference(
    messages,
    temperature = 1.0,
    top_p = 0.95,
    top_k = 40,
    min_p = 0.01,
    repetition_penalty = 1.0,
):
    messages = messages.copy()
    openai_client = OpenAI(
        base_url = "http://127.0.0.1:8001/v1",
        api_key = "sk-no-key-required",
    )
    model_name = next(iter(openai_client.models.list())).id
    print(f"使用模型 = {model_name}")
    has_tool_calls = True
    original_messages_len = len(messages)
    while has_tool_calls:
        print(f"当前消息 = {messages}")
        response = openai_client.chat.completions.create(
            model = model_name,
            messages = messages,
            temperature = temperature,
            top_p = top_p,
            tools = tools if tools else None,
            tool_choice = "auto" if tools else None,
            extra_body = {"top_k": top_k, "min_p": min_p, "repetition_penalty" :repetition_penalty,}
        )
        tool_calls = response.choices[0].message.tool_calls or []
        content = response.choices[0].message.content or ""
        tool_calls_dict = [tc.to_dict() for tc in tool_calls] if tool_calls else tool_calls
        messages.append({"role": "assistant", "tool_calls": tool_calls_dict, "content": content,})
        for tool_call in tool_calls:
            fx, args, _id = tool_call.function.name, tool_call.function.arguments, tool_call.id
            out = MAP_FN[fx](**json.loads(args))
            messages.append({"role": "tool", "tool_call_id": _id, "name": fx, "content": str(out),})
        else:
            has_tool_calls = False
    return messages


执行生成的 Python 代码
    messages = [{
    "role": "user",
    "content": [{"type": "text", "text": "用 Python 创建一个斐波那契函数并计算 fib(20)。"}],
}]
unsloth_inference(messages, temperature = 1.0, top_p = 0.95, top_k = 40, min_p = 0.00)

执行任意终端命令
messages = [{
    "role": "user",
    "content": [{"type": "text", "text": "将 'I'm a happy Sloth' 写入文件，然后把它打印回来给我。"}],
}]
messages = unsloth_inference(messages, temperature = 1.0, top_p = 1.0, top_k = 40, min_p = 0.00)