#!/usr/bin/env python3
"""
使用 Transformers + GLM-OCR 对图片进行 OCR
"""

import sys
import os

# 模型路径和图片路径
MODEL_PATH = "/mnt/c/AI/LLM/models/vision-language-models/GLM/GLM-OCR"
IMAGE_PATH = "/mnt/c/AI/LLM/1.jpg"


def ocr_image(image_path: str, prompt: str = "Text Recognition:"):
    """对图片进行 OCR"""
    try:
        from transformers import AutoProcessor, AutoModelForImageTextToText
        import torch

        print("=" * 60)
        print("GLM-OCR 图片识别")
        print("=" * 60)
        print(f"模型路径: {MODEL_PATH}")
        print(f"图片路径: {image_path}")
        print(f"提示词: {prompt}")

        # 检查文件
        if not os.path.exists(image_path):
            print(f"❌ 错误: 图片不存在: {image_path}")
            return False

        print("\n正在加载处理器...")
        processor = AutoProcessor.from_pretrained(
            MODEL_PATH,
            trust_remote_code=True
        )
        print("✅ 处理器加载成功!")

        print("\n正在加载模型...")
        model = AutoModelForImageTextToText.from_pretrained(
            MODEL_PATH,
            trust_remote_code=True,
            torch_dtype=torch.bfloat16,
            device_map="auto"
        )
        print(f"✅ 模型加载成功! (设备: {model.device}, 类型: {model.dtype})")

        # 准备消息
        print("\n正在处理图片...")
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "url": image_path
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ],
            }
        ]

        # 处理输入
        inputs = processor.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_dict=True,
            return_tensors="pt"
        ).to(model.device)

        inputs.pop("token_type_ids", None)

        # 生成
        print("正在识别...")
        with torch.no_grad():
            generated_ids = model.generate(**inputs, max_new_tokens=8192)

        # 解码输出
        output_text = processor.decode(
            generated_ids[0][inputs["input_ids"].shape[1]:],
            skip_special_tokens=False
        )

        print("\n" + "=" * 60)
        print("OCR 结果:")
        print("=" * 60)
        print(output_text)
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n❌ OCR 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # 支持命令行参数
    image_path = sys.argv[1] if len(sys.argv) > 1 else IMAGE_PATH
    prompt = sys.argv[2] if len(sys.argv) > 2 else "Text Recognition:"

    success = ocr_image(image_path, prompt)
    sys.exit(0 if success else 1)
