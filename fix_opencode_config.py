#!/usr/bin/env python3
"""修复 OpenCode 配置文件的视觉模型 capabilities"""

import json
import sys

# 读取配置文件
config_path = "C:\\Users\\ADMIN\\.config\\opencode\\opencode.json"

try:
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # 修改 llamaccp provider 中的 qwen3.5-9b-ud-q4-vision
    if 'provider' in config and 'llamaccp' in config['provider']:
        models = config['provider']['llamaccp'].get('models', {})
        
        if 'qwen3.5-9b-ud-q4-vision' in models:
            # 尝试不同的 capabilities 格式
            models['qwen3.5-9b-ud-q4-vision']['capabilities'] = {
                "vision": True,
                "images": True,
                "multimodal": True
            }
            print("✓ 已更新 qwen3.5-9b-ud-q4-vision 的 capabilities")
        else:
            print("✗ 未找到 qwen3.5-9b-ud-q4-vision 模型")
            sys.exit(1)
    else:
        print("✗ 未找到 llamaccp provider")
        sys.exit(1)
    
    # 保存配置文件
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print(f"✓ 配置文件已保存到: {config_path}")
    print("\n请完全重启 OpenCode 客户端使配置生效！")
    
except Exception as e:
    print(f"✗ 错误: {e}")
    sys.exit(1)
