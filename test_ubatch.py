#!/usr/bin/env python3
"""测试 ubatch_size 参数是否正确读取"""

import yaml

# 读取模型配置
config_path = "configs/models.yaml"
with open(config_path, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

# 查找 qwen3.5-27b-instruct-reasoning 模型
for model in config.get('models', []):
    if model.get('id') == 'qwen3.5-27b-instruct-reasoning':
        print("=" * 50)
        print(f"模型: {model.get('name')}")
        print(f"ID: {model.get('id')}")
        print("=" * 50)
        print(f"batch_size: {model.get('batch_size', '未设置')}")
        print(f"ubatch_size: {model.get('ubatch_size', '未设置')}")
        print(f"max_context: {model.get('max_context', '未设置')}")
        print(f"parallel: {model.get('parallel', '未设置')}")
        print("=" * 50)
        
        # 模拟 llama_backend.py 的参数读取
        batch_size = model.get('batch_size', 2048)
        ubatch_size = model.get('ubatch_size', batch_size)
        
        print("\n启动参数将会是:")
        print(f"  -b {batch_size}    (batch_size)")
        print(f"  -ub {ubatch_size}   (ubatch_size)")
        break
else:
    print("未找到 qwen3.5-27b-instruct-reasoning 模型")
