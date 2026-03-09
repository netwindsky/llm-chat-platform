import yaml
import os
import re
from pathlib import Path

# 读取配置文件
with open('configs/models.yaml', 'r', encoding='utf-8') as f:
    content = f.read()

# 获取所有实际存在的模型文件
actual_files = {}
models_dir = Path('models')
for file in models_dir.rglob('*.gguf'):
    filename = file.name.lower()
    rel_path = file.relative_to(models_dir.parent).as_posix()
    actual_files[filename] = rel_path

# 缺失模型到实际文件的映射
missing_to_actual = {
    # DeepSeek 模型
    'deepseek-r1-0528-qwen3-8b-ud-q4-xl.gguf': 'language-models/DeepSeek/DeepSeek-R1-0528-Qwen3-8B-UD-Q4_K_XL.gguf',
    'deepseek-r1-distill-llama-8b-ud-q4-xl.gguf': 'language-models/DeepSeek/DeepSeek-R1-Distill-Llama-8B-UD-Q4_K_XL.gguf',
    'deepseek-r1-distill-qwen-14b-q4-m.gguf': 'language-models/DeepSeek/DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf',
    'deepseek-r1-distill-qwen-32b-q4-m.gguf': 'language-models/DeepSeek/DeepSeek-R1-Distill-Qwen-32B-Q4_K_M.gguf',

    # GLM 模型
    'glm-4-32b-0414-ud-q4-xl.gguf': 'language-models/GLM/GLM-4-32B-0414-UD-Q4_K_XL.gguf',

    # Gemma 模型
    'gemma-3-12b-it-ud-q4-xl.gguf': 'language-models/Gemma/gemma-3-12b-it-UD-Q4_K_XL.gguf',
    'gemma-3-27b-it-ud-q4-xl.gguf': 'language-models/Gemma/gemma-3-27b-it-UD-Q4_K_XL.gguf',

    # ERNIE 模型
    'ernie-4.5-21b-thinking.gguf': 'language-models/ERNIE/ERNIE-4.5-21B-A3B-Thinking-UD-Q4_K_XL.gguf',

    # Phi 模型
    'phi-4-reasoning-plus-ud-q4-xl.gguf': 'language-models/Phi/Phi-4-reasoning-plus-UD-Q4_K_XL.gguf',

    # Qwen Coder 模型
    'qwen-coder-30b-a3b-instruct.gguf': 'code-models/Qwen-Coder/Qwen3-Coder-30B-A3B-Instruct-UD-Q4_K_XL.gguf',
    'qwen-coder-30b-a3b-instruct-1m.gguf': 'code-models/Qwen-Coder/Qwen3-Coder-30B-A3B-Instruct-1M-UD-Q4_K_XL.gguf',

    # Embedding 模型
    'snowflake-arctic-embed-l.gguf': 'embedding-models/snowflake-arctic-embed-l--Q4_K_M.GGUF',
}

# 解析 YAML 获取模型配置
with open('configs/models.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

fixes = []

for model in config.get('models', []):
    model_id = model.get('id', 'unknown')
    config_path = model.get('path', '')

    if not config_path:
        continue

    config_filename = Path(config_path).name.lower()

    # 检查是否在缺失映射中
    if config_filename in missing_to_actual:
        new_path = missing_to_actual[config_filename]
        if config_path != new_path:
            fixes.append({
                'model_id': model_id,
                'old_path': config_path,
                'new_path': new_path
            })

print(f"找到 {len(fixes)} 个缺失模型可以修复:\n")
for fix in fixes:
    print(f"模型: {fix['model_id']}")
    print(f"  旧路径: {fix['old_path']}")
    print(f"  新路径: {fix['new_path']}")
    print()

# 执行修复
if fixes:
    print("正在修复...")
    for fix in fixes:
        old_path = fix['old_path']
        new_path = fix['new_path']
        # 使用正则表达式替换
        pattern = rf'(path:\s*){re.escape(old_path)}'
        replacement = rf'\g<1>{new_path}'
        content = re.sub(pattern, replacement, content)
        print(f"  已修复: {fix['model_id']}")

    # 写回文件
    with open('configs/models.yaml', 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"\n完成！共修复 {len(fixes)} 个模型路径。")
else:
    print("没有需要修复的路径。")

# 检查是否还有缺失的
print("\n" + "="*80)
print("检查是否还有缺失的模型...")
print("="*80)

with open('configs/models.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

still_missing = []
for model in config.get('models', []):
    model_id = model.get('id', 'unknown')
    config_path = model.get('path', '')
    if not config_path:
        continue
    full_path = Path('models') / config_path
    if not full_path.exists():
        still_missing.append(model_id)

if still_missing:
    print(f"\n仍有 {len(still_missing)} 个模型缺失:")
    for m in still_missing:
        print(f"  - {m}")
else:
    print("\n所有模型路径都已正确！")
