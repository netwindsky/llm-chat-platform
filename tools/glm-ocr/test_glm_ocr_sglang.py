#!/usr/bin/env python3
"""
使用 SGLang 测试 GLM-OCR 模型
"""

import os
import sys

# 模型路径
MODEL_PATH = "/mnt/c/AI/LLM/models/vision-language-models/GLM/GLM-OCR"

def test_with_sglang():
    """使用 SGLang 加载和测试 GLM-OCR"""
    try:
        import sglang as sgl
        from sglang import Runtime

        print("=" * 60)
        print("使用 SGLang 测试 GLM-OCR")
        print("=" * 60)
        print(f"模型路径: {MODEL_PATH}")

        # 检查模型路径是否存在
        if not os.path.exists(MODEL_PATH):
            print(f"错误: 模型路径不存在: {MODEL_PATH}")
            return False

        print("模型文件存在，开始加载...")

        # 创建 SGLang Runtime
        runtime = Runtime(
            model_path=MODEL_PATH,
            tp_size=1,  # Tensor parallelism size
            dtype="bfloat16",
            trust_remote_code=True,
        )

        print("模型加载成功!")

        # 创建生成器
        @sgl.function
        def ocr_func(s, image_path, prompt="Text Recognition:"):
            s += sgl.user(sgl.image(image_path) + prompt)
            s += sgl.assistant(sgl.gen("answer", max_tokens=4096))

        # 测试推理
        print("\n测试推理...")
        state = ocr_func.run(
            image_path="test_image.png",  # 需要替换为实际图片路径
            prompt="请识别这张图片中的文字"
        )

        print(f"结果: {state['answer']}")

        runtime.shutdown()
        return True

    except Exception as e:
        print(f"SGLang 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_with_transformers():
    """使用 Transformers 作为备选方案"""
    try:
        from transformers import AutoProcessor, AutoModelForImageTextToText
        import torch

        print("\n" + "=" * 60)
        print("使用 Transformers 测试 GLM-OCR")
        print("=" * 60)

        print(f"模型路径: {MODEL_PATH}")
        print("正在加载模型...")

        processor = AutoProcessor.from_pretrained(
            MODEL_PATH,
            trust_remote_code=True
        )

        model = AutoModelForImageTextToText.from_pretrained(
            MODEL_PATH,
            trust_remote_code=True,
            torch_dtype=torch.bfloat16,
            device_map="auto"
        )

        print("模型加载成功!")
        print(f"设备: {model.device}")
        print(f"数据类型: {model.dtype}")

        return True

    except Exception as e:
        print(f"Transformers 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("GLM-OCR 测试脚本")
    print("=" * 60)

    # 首先尝试 SGLang
    if not test_with_sglang():
        print("\nSGLang 测试失败，尝试 Transformers...")
        test_with_transformers()
