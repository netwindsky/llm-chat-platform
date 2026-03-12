#!/usr/bin/env python3
"""分析测试文件并识别无用/重复的文件"""

import os
import re
from pathlib import Path
from collections import defaultdict

# 测试文件列表
test_files = [
    "test_red_big.png",
    "test_red.png", 
    "test_38520.py",
    "test_adapter_convert.py",
    "test_adapter.py",
    "test_anthropic_api.py",
    "test_anthropic_complete.py",
    "test_anthropic_simple.py",
    "test_anthropic_tools.py",
    "test_beta.py",
    "test_check_format.py",
    "test_check_response.py",
    "test_compare.py",
    "test_current_adapter.py",
    "test_debug_system.py",
    "test_debug_tags.py",
    "test_final.py",
    "test_full_tool_flow.py",
    "test_full_tool.py",
    "test_llama_direct.py",
    "test_response_format.py",
    "test_stream_debug.py",
    "test_stream_format.py",
    "test_stream_tool.py",
    "test_streaming.py",
    "test_system_content.py",
    "test_system_list_api.py",
    "test_system_list_full.py",
    "test_system_list.py",
    "test_system_no_tools.py",
    "test_tool_call_debug.py",
    "test_ubatch.py",
    "test_v1v1.py"
]

# 分类规则
categories = {
    "图片文件": [".png"],
    "Anthropic API 测试": ["anthropic"],
    "适配器测试": ["adapter"],
    "流式响应测试": ["stream"],
    "系统消息测试": ["system"],
    "工具调用测试": ["tool"],
    "响应格式测试": ["format", "response", "check"],
    "调试测试": ["debug"],
    "完整流程测试": ["full", "complete", "final"],
    "其他测试": []
}

# 分析每个文件
file_analysis = {}

for filename in test_files:
    filepath = Path(f"c:\\AI\\LLM\\{filename}")
    
    if not filepath.exists():
        file_analysis[filename] = {"exists": False, "category": "不存在", "size": 0}
        continue
    
    size = filepath.stat().st_size
    
    # 确定分类
    category = "其他测试"
    for cat_name, keywords in categories.items():
        for keyword in keywords:
            if keyword in filename.lower():
                category = cat_name
                break
        if category != "其他测试":
            break
    
    # 读取文件内容分析
    content_preview = ""
    if filename.endswith('.py'):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')[:10]
                content_preview = '\n'.join(lines)
        except:
            content_preview = "无法读取"
    
    file_analysis[filename] = {
        "exists": True,
        "category": category,
        "size": size,
        "preview": content_preview[:200] if content_preview else ""
    }

# 按分类输出
print("=" * 80)
print("测试文件分析报告")
print("=" * 80)

for category in categories.keys():
    files_in_cat = [f for f, info in file_analysis.items() if info["category"] == category and info["exists"]]
    if files_in_cat:
        print(f"\n【{category}】({len(files_in_cat)}个文件)")
        print("-" * 80)
        for filename in sorted(files_in_cat):
            info = file_analysis[filename]
            size_kb = info["size"] / 1024
            print(f"  • {filename:<35} ({size_kb:.1f} KB)")

# 识别重复/冗余文件
print("\n" + "=" * 80)
print("重复/冗余文件识别")
print("=" * 80)

# 1. 图片文件 - 保留一个即可
png_files = [f for f in test_files if f.endswith('.png')]
if len(png_files) > 1:
    print(f"\n【图片文件冗余】保留一个即可:")
    for f in png_files:
        info = file_analysis.get(f, {})
        if info.get("exists"):
            print(f"  ⚠️  {f} ({info['size']/1024:.1f} KB) - 建议删除")

# 2. 功能重复的测试
similar_tests = {
    "Anthropic API 基础测试": ["test_anthropic_simple.py", "test_anthropic_api.py"],
    "响应格式检查": ["test_check_format.py", "test_check_response.py", "test_response_format.py"],
    "流式测试": ["test_stream_debug.py", "test_stream_format.py", "test_stream_tool.py", "test_streaming.py"],
    "系统消息测试": ["test_system_list.py", "test_system_list_api.py", "test_system_list_full.py", "test_system_no_tools.py", "test_system_content.py"],
    "工具调用测试": ["test_tool_call_debug.py", "test_full_tool.py", "test_full_tool_flow.py", "test_final.py"],
    "适配器测试": ["test_adapter.py", "test_adapter_convert.py", "test_current_adapter.py"],
    "调试测试": ["test_debug_system.py", "test_debug_tags.py"]
}

for test_name, files in similar_tests.items():
    existing = [f for f in files if file_analysis.get(f, {}).get("exists", False)]
    if len(existing) > 1:
        print(f"\n【{test_name}】功能重复，建议保留最新版本:")
        for f in existing:
            print(f"  ⚠️  {f}")

# 3. 建议删除的文件
print("\n" + "=" * 80)
print("建议删除的文件列表")
print("=" * 80)

to_delete = []

# 图片文件保留一个
if len(png_files) > 1:
    to_delete.extend(png_files[1:])  # 保留第一个，删除其余的

# 功能重复的测试文件（保留最新的）
redundant = [
    "test_anthropic_simple.py",  # 被 test_anthropic_api.py 覆盖
    "test_check_response.py",    # 被 test_check_format.py 覆盖
    "test_stream_format.py",     # 被 test_streaming.py 覆盖
    "test_stream_tool.py",       # 被 test_streaming.py 覆盖
    "test_system_list.py",       # 被 test_system_list_api.py 覆盖
    "test_system_no_tools.py",   # 被 test_system_list_full.py 覆盖
    "test_system_content.py",    # 被 test_system_list_full.py 覆盖
    "test_tool_call_debug.py",   # 被 test_full_tool.py 覆盖
    "test_final.py",             # 被 test_full_tool_flow.py 覆盖
    "test_adapter.py",           # 被 test_adapter_convert.py 覆盖
    "test_current_adapter.py",   # 被 test_adapter_convert.py 覆盖
    "test_debug_tags.py",        # 被 test_debug_system.py 覆盖
    "test_compare.py",           # 临时测试
    "test_v1v1.py",              # 临时测试
    "test_beta.py",              # 临时测试
]

for f in redundant:
    if file_analysis.get(f, {}).get("exists", False):
        to_delete.append(f)

print(f"\n共建议删除 {len(to_delete)} 个文件:\n")
for f in sorted(set(to_delete)):
    info = file_analysis.get(f, {})
    if info.get("exists"):
        size_kb = info['size'] / 1024
        print(f"  🗑️  {f:<35} ({size_kb:.1f} KB)")

# 建议保留的核心测试文件
print("\n" + "=" * 80)
print("建议保留的核心测试文件")
print("=" * 80)

core_tests = [
    ("test_red.png", "测试图片"),
    ("test_38520.py", "主API端口测试"),
    ("test_anthropic_complete.py", "完整Anthropic API测试"),
    ("test_anthropic_tools.py", "工具调用测试"),
    ("test_llama_direct.py", "直接测试llama-server"),
    ("test_ubatch.py", "ubatch参数测试"),
    ("test_streaming.py", "流式响应测试"),
    ("test_system_list_full.py", "系统消息完整测试"),
    ("test_adapter_convert.py", "适配器转换测试"),
    ("test_full_tool_flow.py", "完整工具调用流程"),
    ("test_debug_system.py", "系统调试"),
]

print()
for f, desc in core_tests:
    if file_analysis.get(f, {}).get("exists", False):
        print(f"  ✅ {f:<35} - {desc}")

print("\n" + "=" * 80)
