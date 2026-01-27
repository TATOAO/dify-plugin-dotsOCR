#!/usr/bin/env python3
"""
使用 tests 文件夹中的 PDF 文件进行实际解析测试
测试 dots_ocr 服务的完整流程，包括超时设置和错误处理
"""

import os
import sys
import time
from pathlib import Path
from io import BytesIO
from typing import Any, Dict

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
dots_ocr_path = project_root / "dots_ocr"
sys.path.insert(0, str(dots_ocr_path))
sys.path.insert(0, str(project_root))

from tools.document_parsing import DocumentParsingTool


class MockFile:
    """模拟 Dify 文件对象 - 直接访问 blob"""
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.transfer_method = "local_file"
        
        # 读取文件内容
        with open(file_path, 'rb') as f:
            self._content = f.read()
        
        # 设置文件属性
        self.extension = Path(file_path).suffix.lower()
        self.mime_type = "application/pdf" if self.extension == ".pdf" else "image/png"
        self.filename = Path(file_path).name
    
    @property
    def blob(self):
        """直接返回文件内容（模拟 blob 可访问）"""
        return self._content


class MockRuntime:
    """模拟 Dify Runtime 对象"""
    def __init__(self, endpoint: str = None, model_name: str = "model", api_key: str = "0", files_url: str = ""):
        self.credentials = {
            "endpoint": endpoint or os.environ.get("DOTS_OCR_ENDPOINT", "http://172.20.201.93:8001/v1"),
            "model_name": model_name or os.environ.get("DOTS_OCR_MODEL", "model"),
            "api_key": api_key or os.environ.get("DOTS_OCR_API_KEY", "0"),
            "files_url": files_url or os.environ.get("FILES_URL", "")
        }


def test_pdf_parsing():
    """测试 PDF 文件解析 - 直接使用客户端"""
    print("=" * 80)
    print("PDF 文件解析测试（完整文档）")
    print("=" * 80)
    
    # 获取配置
    endpoint = os.environ.get("DOTS_OCR_ENDPOINT", "http://172.20.201.93:8001/v1")
    model_name = os.environ.get("DOTS_OCR_MODEL", "model")
    api_key = os.environ.get("DOTS_OCR_API_KEY", "0")
    
    print(f"Endpoint: {endpoint}")
    print(f"Model: {model_name}")
    print(f"Timeout: 300 seconds")
    print()
    
    # 检查 PDF 文件
    pdf_path = project_root / "tests" / "43类合同风险清单.pdf"
    if not pdf_path.exists():
        print(f"错误: 测试文件不存在: {pdf_path}")
        return
    
    file_size = pdf_path.stat().st_size / (1024 * 1024)  # MB
    print(f"测试文件: {pdf_path.name}")
    print(f"文件大小: {file_size:.2f} MB")
    
    # 读取 PDF 文件
    with open(pdf_path, 'rb') as f:
        pdf_content = f.read()
    
    print()
    print("开始解析 PDF...")
    print("注意: 这可能需要几分钟时间，取决于 PDF 的页数和服务器性能")
    print()
    
    from dify_plugin_dotsocr.client import DotsOCRClient
    
    # 创建客户端
    client = DotsOCRClient(
        endpoint=endpoint,
        model_name=model_name,
        api_key=api_key,
        timeout=300
    )
    
    start_time = time.time()
    errors = []
    
    try:
        # 解析 PDF
        results = client.parse_pdf(
            pdf_content,
            prompt_mode="prompt_layout_all_en",
            max_concurrency=2  # 使用较小的并发数进行测试
        )
        
        elapsed_time = time.time() - start_time
        
        print()
        print("=" * 80)
        print("测试完成")
        print("=" * 80)
        print(f"总耗时: {elapsed_time:.2f} 秒 ({elapsed_time/60:.2f} 分钟)")
        print(f"解析页数: {len(results)}")
        
        # 检查错误
        error_pages = []
        success_pages = []
        
        for item in results:
            page_num = item.get('page', '?')
            content = item.get('content', '')
            
            if isinstance(content, str) and content.startswith('Error:'):
                error_pages.append((page_num, content))
                errors.append(content)
            else:
                success_pages.append(page_num)
        
        if error_pages:
            print(f"\n⚠️  错误页数: {len(error_pages)}")
            for page_num, error in error_pages[:5]:  # 只显示前5个错误
                print(f"  页面 {page_num}: {error[:150]}...")
            if len(error_pages) > 5:
                print(f"  ... 还有 {len(error_pages) - 5} 个错误")
        else:
            print("\n✓ 所有页面解析成功，没有错误")
        
        print(f"\n✓ 成功解析页数: {len(success_pages)}")
        
        # 显示前几页的摘要
        print("\n前几页解析结果摘要:")
        for item in results[:3]:
            page_num = item.get('page', '?')
            content = item.get('content', '')
            
            if isinstance(content, str):
                if content.startswith('Error:'):
                    print(f"  页面 {page_num}: ✗ {content[:100]}...")
                else:
                    # 尝试解析 JSON
                    try:
                        import json
                        json_data = json.loads(content)
                        if isinstance(json_data, list):
                            print(f"  页面 {page_num}: ✓ JSON 数组，包含 {len(json_data)} 个元素")
                        elif isinstance(json_data, dict):
                            print(f"  页面 {page_num}: ✓ JSON 对象，包含 {len(json_data)} 个键")
                        else:
                            print(f"  页面 {page_num}: ✓ 内容长度 {len(content)} 字符")
                    except:
                        print(f"  页面 {page_num}: ✓ 内容长度 {len(content)} 字符")
            else:
                print(f"  页面 {page_num}: ✓ 已解析")
        
        if len(results) > 3:
            print(f"  ... 还有 {len(results) - 3} 页")
        
        # 显示总内容统计
        total_chars = sum(len(str(item.get('content', ''))) for item in results)
        print(f"\n总内容大小: {total_chars:,} 字符")
        
    except KeyboardInterrupt:
        print("\n\n用户中断测试")
        elapsed_time = time.time() - start_time
        print(f"已运行时间: {elapsed_time:.2f} 秒")
    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"\n✗ 测试失败 (运行时间: {elapsed_time:.2f} 秒)")
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()


def test_pdf_parsing_single_page():
    """测试单页解析（更快）"""
    print("\n" + "=" * 80)
    print("单页解析测试（快速测试）")
    print("=" * 80)
    
    # 这个测试需要直接使用客户端，只解析第一页
    from dify_plugin_dotsocr.client import DotsOCRClient
    import fitz  # PyMuPDF
    from PIL import Image
    
    endpoint = os.environ.get("DOTS_OCR_ENDPOINT", "http://172.20.201.93:8001/v1")
    model_name = os.environ.get("DOTS_OCR_MODEL", "model")
    api_key = os.environ.get("DOTS_OCR_API_KEY", "0")
    
    pdf_path = project_root / "tests" / "43类合同风险清单.pdf"
    if not pdf_path.exists():
        print(f"错误: 测试文件不存在: {pdf_path}")
        return
    
    print(f"只解析第一页进行快速测试...")
    
    try:
        # 读取 PDF 第一页
        doc = fitz.open(str(pdf_path))
        if len(doc) == 0:
            print("错误: PDF 文件为空")
            return
        
        page = doc[0]
        pix = page.get_pixmap(dpi=200)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        doc.close()
        
        print(f"图像尺寸: {img.size}")
        print()
        
        # 创建客户端
        client = DotsOCRClient(
            endpoint=endpoint,
            model_name=model_name,
            api_key=api_key,
            timeout=300
        )
        
        print("开始推理...")
        start_time = time.time()
        
        result = client.inference(img, prompt_mode="prompt_layout_all_en")
        
        elapsed_time = time.time() - start_time
        
        print(f"✓ 推理成功 (耗时: {elapsed_time:.2f} 秒)")
        print(f"结果长度: {len(result)} 字符")
        print(f"\n结果预览 (前500字符):")
        print("-" * 80)
        print(result[:500])
        print("-" * 80)
        
        # 尝试解析为 JSON
        try:
            import json
            json_data = json.loads(result)
            print(f"\n✓ 结果可以解析为 JSON")
            if isinstance(json_data, list):
                print(f"  包含 {len(json_data)} 个元素")
            elif isinstance(json_data, dict):
                print(f"  包含 {len(json_data)} 个键")
        except json.JSONDecodeError:
            print(f"\n⚠️  结果不是有效的 JSON 格式")
        
    except Exception as e:
        print(f"\n✗ 测试失败")
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="测试 PDF 解析")
    parser.add_argument("--single-page", action="store_true", help="只测试单页解析（更快）")
    args = parser.parse_args()
    
    if args.single_page:
        test_pdf_parsing_single_page()
    else:
        test_pdf_parsing()
        print("\n提示: 使用 --single-page 参数可以只测试单页解析（更快）")
