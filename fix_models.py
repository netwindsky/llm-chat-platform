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
    if filename not in actual_files:
        actual_files[filename] = []
    actual_files[filename].append(rel_path)

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
    full_path = Path('models') / config_path

    # 如果文件不存在
    if not full_path.exists():
        # 查找是否有匹配的文件名（忽略大小写）
        if config_filename in actual_files:
            # 找到实际路径
            actual_paths = actual_files[config_filename]
            if len(actual_paths) == 1:
                actual_path = actual_paths[0]
                # 提取相对路径部分（去掉 models/ 前缀）
                new_path = actual_path.replace('models/', '', 1)

                if config_path != new_path:
                    fixes.append({
                        'model_id': model_id,
                        'old_path': config_path,
                        'new_path': new_path
                    })

print(f"找到 {len(fixes)} 个需要修复的路径:\n")
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
        # 使用正则表达式替换，确保只替换 path: 后面的路径
        pattern = rf'(path:\s*){re.escape(old_path)}'
        replacement = rf'\g<1>{new_path}'
        content = re.sub(pattern, replacement, content)
        print(f"  已修复: {fix['model_id']}")

    # 写回文件
    with open('configs/models.yaml', 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"\n完成！共修复 {len(fixes)} 个路径。")
else:
    print("没有需要修复的路径。")

# 列出缺失的模型
print("\n" + "="*80)
print("以下模型文件确实不存在（需要下载）:")
print("="*80)
missing_count = 0
for model in config.get('models', []):
    model_id = model.get('id', 'unknown')
    config_path = model.get('path', '')
    if not config_path:
        continue
    config_filename = Path(config_path).name.lower()
    full_path = Path('models') / config_path
    if not full_path.exists() and config_filename not in actual_files:
        missing_count += 1
        print(f"  {model_id}: {config_path}")

print(f"\n共 {missing_count} 个模型缺失")
