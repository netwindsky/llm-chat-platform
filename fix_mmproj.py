import re

# 读取文件
with open('configs/models.yaml', 'r', encoding='utf-8') as f:
    content = f.read()

# 修复 mmproj 路径 - 去掉 models/ 前缀
old_pattern = r'mmproj: models/vision-language-models/'
new_pattern = r'mmproj: vision-language-models/'

# 替换
content_new = re.sub(old_pattern, new_pattern, content)

# 统计替换数量
count = len(re.findall(old_pattern, content))

# 写回文件
with open('configs/models.yaml', 'w', encoding='utf-8') as f:
    f.write(content_new)

print(f"已修复 {count} 个 mmproj 路径")
