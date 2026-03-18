#!/usr/bin/env python3
"""
直接使用 Transformers 测试 GLM-OCR（无需 sglang）
"""

import sys
import os

# 模型路径
MODEL_PATH = "/mnt/c/AI/LLM/models/vision-language-models/GLM/GLM-OCR"

def test_glm_ocr():
    """直接使用 Transformers 加载和测试 GLM-OCR"""
    try:
        from transformers import AutoProcessor, AutoModelForImageTextToText
        import torch

        print("=" * 60)
        print("使用 Transformers 直接测试 GLM-OCR")
        print("=" * 60)
        print(f"模型路径: {MODEL_PATH}")

        # 检查模型路径
        if not os.path.exists(MODEL_PATH):
            print(f"错误: 模型路径不存在: {MODEL_PATH}")
            return False

        print("\n正在加载处理器...")
        processor = AutoProcessor.from_pretrained(
            MODEL_PATH,
            trust_remote_code=True
        )
        print("处理器加载成功!")

        print("\n正在加载模型...")
        model = AutoModelForImageTextToText.from_pretrained(
            MODEL_PATH,
            trust_remote_code=True,
            torch_dtype=torch.bfloat16,
            device_map="auto"
        )
        print("模型加载成功!")
        print(f"设备: {model.device}")
        print(f"数据类型: {model.dtype}")

        # 测试文本生成（不需要图片，先测试模型是否能运行）
        print("\n测试模型推理...")
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Hello"
                    }
                ],
            }
        ]

        inputs = processor.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_dict=True,
            return_tensors="pt"
        ).to(model.device)

        inputs.pop("token_type_ids", None)

        print("生成中...")
        with torch.no_grad():
            generated_ids = model.generate(**inputs, max_new_tokens=50)

        output_text = processor.decode(
            generated_ids[0][inputs["input_ids"].shape[1]:],
            skip_special_tokens=True
        )

        print(f"\n输出: {output_text}")
        print("\n✅ GLM-OCR 测试成功!")
        return True

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_glm_ocr()
    sys.exit(0 if success else 1)
