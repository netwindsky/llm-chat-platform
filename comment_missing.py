import yaml
import re
from pathlib import Path

# 需要注释掉的模型ID
missing_models = [
    'qwen3.5-35b-a3b-thinking',
    'qwen3.5-35b-a3b-no-thinking',
    'qwen3.5-35b-a3b-vision',
    'glm-4.7-flash-ud-q4-tools',
    'sglang-qwen2.5-7b'
]

# 读取文件
with open('configs/models.yaml', 'r', encoding='utf-8') as f:
    content = f.read()

# 解析YAML
with open('configs/models.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

# 找到每个缺失模型的起始和结束位置
lines = content.split('\n')
commented_count = 0

for model_id in missing_models:
    # 查找模型定义的起始行
    start_idx = None
    for i, line in enumerate(lines):
        if f'- id: {model_id}' in line:
            start_idx = i
            break

    if start_idx is None:
        print(f"未找到模型: {model_id}")
        continue

    # 查找模型定义的结束位置（下一个模型的注释开始或文件结束）
    end_idx = len(lines)
    for i in range(start_idx + 1, len(lines)):
        if lines[i].strip().startswith('# ----') or lines[i].strip().startswith('- id:'):
            end_idx = i
            break

    # 注释掉这一段
    for i in range(start_idx, end_idx):
        if lines[i].strip() and not lines[i].strip().startswith('#'):
            lines[i] = '# ' + lines[i]

    commented_count += 1
    print(f"已注释: {model_id} (第 {start_idx+1} 行到第 {end_idx} 行)")

# 写回文件
with open('configs/models.yaml', 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

print(f"\n完成！共注释掉 {commented_count} 个缺失的模型配置。")
