import yaml
import os
from pathlib import Path

# 读取配置文件
with open('configs/models.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

# 获取所有实际存在的模型文件
actual_files = set()
models_dir = Path('models')
for file in models_dir.rglob('*.gguf'):
    # 转换为相对路径，使用正斜杠
    rel_path = file.relative_to(models_dir.parent).as_posix()
    actual_files.add(rel_path)

print("=" * 80)
print("实际存在的模型文件:")
print("=" * 80)
for f in sorted(actual_files):
    print(f"  {f}")

print("\n" + "=" * 80)
print("配置文件中定义的模型路径:")
print("=" * 80)

# 检查每个配置的模型
missing_models = []
wrong_path_models = []

for model in config.get('models', []):
    model_id = model.get('id', 'unknown')
    config_path = model.get('path', '')

    if not config_path:
        continue

    # 检查文件是否存在
    full_path = Path('models') / config_path
    exists = full_path.exists()

    if not exists:
        # 检查是否是路径错误（文件名存在但路径不同）
        filename = Path(config_path).name
        found = False
        for actual in actual_files:
            if Path(actual).name.lower() == filename.lower():
                wrong_path_models.append({
                    'id': model_id,
                    'config_path': config_path,
                    'actual_path': actual,
                    'filename': filename
                })
                found = True
                break

        if not found:
            missing_models.append({
                'id': model_id,
                'config_path': config_path,
                'filename': filename
            })

print("\n" + "=" * 80)
print(f"路径错误（文件存在但路径不对）: {len(wrong_path_models)} 个")
print("=" * 80)
for m in wrong_path_models:
    print(f"\n  模型 ID: {m['id']}")
    print(f"  配置路径: {m['config_path']}")
    print(f"  实际路径: {m['actual_path']}")
    print(f"  文件名: {m['filename']}")

print("\n" + "=" * 80)
print(f"文件缺失（完全找不到）: {len(missing_models)} 个")
print("=" * 80)
for m in missing_models:
    print(f"\n  模型 ID: {m['id']}")
    print(f"  配置路径: {m['config_path']}")
    print(f"  文件名: {m['filename']}")

print("\n" + "=" * 80)
print("总结:")
print("=" * 80)
print(f"  总配置模型数: {len(config.get('models', []))}")
print(f"  实际文件数: {len(actual_files)}")
print(f"  路径错误: {len(wrong_path_models)}")
print(f"  文件缺失: {len(missing_models)}")
