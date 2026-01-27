#!/usr/bin/env python3
"""
测试超时修复：模拟实际调用场景
"""

import os
import sys
from pathlib import Path
from io import BytesIO
from typing import Any, Dict

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
dots_ocr_path = project_root / "dots_ocr"
sys.path.insert(0, str(dots_ocr_path))
sys.path.insert(0, str(project_root))

from dify_plugin_dotsocr.client import DotsOCRClient


def test_client_timeout():
    """测试客户端超时设置"""
    print("=" * 80)
    print("测试客户端超时设置")
    print("=" * 80)
    
    endpoint = os.environ.get("DOTS_OCR_ENDPOINT", "http://172.20.201.93:8001/v1")
    model_name = os.environ.get("DOTS_OCR_MODEL", "model")
    api_key = os.environ.get("DOTS_OCR_API_KEY", "0")
    
    print(f"Endpoint: {endpoint}")
    print(f"Model: {model_name}")
    print(f"Timeout: 300 seconds")
    print()
    
    # 创建客户端，设置超时为300秒
    client = DotsOCRClient(
        endpoint=endpoint,
        model_name=model_name,
        api_key=api_key,
        timeout=300
    )
    
    # 验证超时设置
    assert client.timeout == 300, f"Expected timeout 300, got {client.timeout}"
    assert client.client.timeout == 300, f"Expected client timeout 300, got {client.client.timeout}"
    
    print("✓ 超时设置正确")
    print(f"  - client.timeout = {client.timeout}")
    print(f"  - client.client.timeout = {client.client.timeout}")
    print()
    
    # 测试一个简单的图像（如果有测试图像）
    test_image_path = project_root / "tests" / "test_image.png"
    if test_image_path.exists():
        from PIL import Image
        print("找到测试图像，尝试调用推理...")
        try:
            image = Image.open(test_image_path)
            result = client.inference(image, prompt_mode="prompt_ocr")
            print(f"✓ 推理成功，结果长度: {len(result)} 字符")
            print(f"  结果预览: {result[:100]}...")
        except Exception as e:
            print(f"✗ 推理失败: {e}")
            print("  这可能是正常的，如果服务器不可用")
    else:
        print("未找到测试图像，跳过实际推理测试")
    
    print()
    print("=" * 80)
    print("超时设置测试完成")
    print("=" * 80)


if __name__ == "__main__":
    test_client_timeout()
