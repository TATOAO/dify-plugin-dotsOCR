#!/usr/bin/env python3
"""
本地测试脚本：测试 DocumentParsingTool 的文件处理逻辑
使用本地PDF文件进行测试，避免每次都要打包和部署到Dify
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

# 直接导入（因为 dots_ocr 是包名）
from tools.document_parsing import DocumentParsingTool


class MockFile:
    """模拟 Dify 文件对象"""
    def __init__(self, file_path: str, transfer_method: str = "local_file", 
                 remote_url: str = None, url: str = None, blob_accessible: bool = False):
        self.file_path = file_path
        self.transfer_method = transfer_method
        self.blob_accessible = blob_accessible
        
        # 读取文件内容
        with open(file_path, 'rb') as f:
            self._content = f.read()
        
        # 设置文件属性
        self.extension = Path(file_path).suffix.lower()
        self.mime_type = "application/pdf" if self.extension == ".pdf" else "image/png"
        self.filename = Path(file_path).name
        
        # 设置URL（模拟Dify的行为）
        if transfer_method == "local_file":
            # 本地上传：使用相对路径
            self.remote_url = remote_url or f"/files/test-id/file-preview?timestamp=1234567890&nonce=test&sign=test"
            self.url = url or self.remote_url
        else:
            # 文件URL：可能是完整URL或相对路径
            self.remote_url = remote_url or f"https://example.com/files/test.pdf"
            self.url = url or self.remote_url
    
    @property
    def blob(self):
        """模拟 blob 属性"""
        if self.blob_accessible:
            return self._content
        else:
            # 模拟 blob 访问失败的情况（FILES_URL未配置）
            raise AttributeError("blob access failed - FILES_URL not configured")


class MockRuntime:
    """模拟 Dify Runtime 对象"""
    def __init__(self, endpoint: str = None, model_name: str = "model", api_key: str = "0"):
        self.credentials = {
            "endpoint": endpoint or os.environ.get("DOTS_OCR_ENDPOINT", "http://localhost:8001/v1"),
            "model_name": model_name,
            "api_key": api_key
        }
        # 可选：模拟 runtime 中的 files_url
        # self.files_url = os.environ.get("FILES_URL", "")


def test_local_file_upload():
    """测试本地上传场景（transfer_method='local_file'）"""
    print("=" * 80)
    print("测试场景 1: 本地上传 (transfer_method='local_file')")
    print("=" * 80)
    
    # 设置 FILES_URL 环境变量（模拟Dify环境）
    os.environ["FILES_URL"] = "http://localhost:5001"
    
    pdf_path = project_root / "tests" / "43类合同风险清单.pdf"
    if not pdf_path.exists():
        print(f"错误: 测试文件不存在: {pdf_path}")
        return
    
    # 创建模拟文件对象
    mock_file = MockFile(
        str(pdf_path),
        transfer_method="local_file",
        remote_url="/files/d2fd660c-4c26-4d77-a776-577ac5e65ab4/file-preview?timestamp=1769422228&nonce=a86adb0e657cd3d2351913a64ac03104&sign=WRPA_9Vybwy5h7saEvofmh5M-QQ3YT-pNPvHG768JGw%3D"
    )
    
    # 创建模拟 runtime
    mock_runtime = MockRuntime()
    
    # 创建工具实例
    tool = DocumentParsingTool()
    tool.runtime = mock_runtime
    
    # 准备参数
    tool_parameters = {
        "file": mock_file,
        "mode": "prompt_layout_all_en",
        "max_concurrency": 2
    }
    
    print(f"文件路径: {pdf_path}")
    print(f"transfer_method: {mock_file.transfer_method}")
    print(f"remote_url: {mock_file.remote_url}")
    print(f"FILES_URL: {os.environ.get('FILES_URL')}")
    print()
    
    # 执行工具
    try:
        print("开始执行工具...")
        messages = list(tool._invoke(tool_parameters))
        
        print(f"\n收到 {len(messages)} 条消息:")
        for i, msg in enumerate(messages, 1):
            print(f"\n消息 {i}:")
            if hasattr(msg, 'type'):
                print(f"  类型: {msg.type}")
            if hasattr(msg, 'message'):
                print(f"  内容: {msg.message[:200]}..." if len(str(msg.message)) > 200 else f"  内容: {msg.message}")
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()


def test_local_file_without_files_url():
    """测试本地上传但未设置FILES_URL的场景"""
    print("\n" + "=" * 80)
    print("测试场景 2: 本地上传但未设置 FILES_URL")
    print("=" * 80)
    
    # 清除 FILES_URL
    if "FILES_URL" in os.environ:
        del os.environ["FILES_URL"]
    
    pdf_path = project_root / "tests" / "43类合同风险清单.pdf"
    if not pdf_path.exists():
        print(f"错误: 测试文件不存在: {pdf_path}")
        return
    
    mock_file = MockFile(
        str(pdf_path),
        transfer_method="local_file",
        remote_url="/files/test-id/file-preview?timestamp=1234567890&nonce=test&sign=test"
    )
    
    mock_runtime = MockRuntime()
    tool = DocumentParsingTool()
    tool.runtime = mock_runtime
    
    tool_parameters = {
        "file": mock_file,
        "mode": "prompt_layout_all_en",
        "max_concurrency": 2
    }
    
    print(f"FILES_URL: {os.environ.get('FILES_URL', '未设置')}")
    print()
    
    try:
        messages = list(tool._invoke(tool_parameters))
        print(f"\n收到 {len(messages)} 条消息:")
        for i, msg in enumerate(messages, 1):
            print(f"\n消息 {i}:")
            if hasattr(msg, 'message'):
                print(f"  内容: {msg.message}")
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()


def test_remote_url():
    """测试文件URL场景（transfer_method='remote_url'）"""
    print("\n" + "=" * 80)
    print("测试场景 3: 文件URL (transfer_method='remote_url')")
    print("=" * 80)
    
    pdf_path = project_root / "tests" / "43类合同风险清单.pdf"
    if not pdf_path.exists():
        print(f"错误: 测试文件不存在: {pdf_path}")
        return
    
    # 模拟远程URL（完整URL）
    mock_file = MockFile(
        str(pdf_path),
        transfer_method="remote_url",
        remote_url="https://example.com/files/test.pdf"
    )
    
    mock_runtime = MockRuntime()
    tool = DocumentParsingTool()
    tool.runtime = mock_runtime
    
    tool_parameters = {
        "file": mock_file,
        "mode": "prompt_layout_all_en",
        "max_concurrency": 2
    }
    
    print(f"remote_url: {mock_file.remote_url}")
    print()
    
    try:
        messages = list(tool._invoke(tool_parameters))
        print(f"\n收到 {len(messages)} 条消息:")
        for i, msg in enumerate(messages, 1):
            print(f"\n消息 {i}:")
            if hasattr(msg, 'message'):
                content = str(msg.message)
                print(f"  内容: {content[:200]}..." if len(content) > 200 else f"  内容: {content}")
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()


def test_direct_blob_access():
    """测试直接访问blob成功的场景（模拟FILES_URL已正确配置）"""
    print("\n" + "=" * 80)
    print("测试场景 4: 直接访问blob成功")
    print("=" * 80)
    
    pdf_path = project_root / "tests" / "43类合同风险清单.pdf"
    if not pdf_path.exists():
        print(f"错误: 测试文件不存在: {pdf_path}")
        return
    
    # 使用 blob_accessible=True 来模拟可以直接访问blob
    mock_file = MockFile(
        str(pdf_path),
        transfer_method="local_file",
        blob_accessible=True
    )
    
    mock_runtime = MockRuntime()
    tool = DocumentParsingTool()
    tool.runtime = mock_runtime
    
    tool_parameters = {
        "file": mock_file,
        "mode": "prompt_layout_all_en",
        "max_concurrency": 2
    }
    
    print("使用直接blob访问（模拟FILES_URL已正确配置）")
    print()
    
    try:
        messages = list(tool._invoke(tool_parameters))
        print(f"\n收到 {len(messages)} 条消息:")
        for i, msg in enumerate(messages, 1):
            print(f"\n消息 {i}:")
            if hasattr(msg, 'message'):
                content = str(msg.message)
                print(f"  内容: {content[:200]}..." if len(content) > 200 else f"  内容: {content}")
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()


def test_url_construction_logic():
    """测试URL拼接逻辑（不实际调用工具）"""
    print("\n" + "=" * 80)
    print("测试场景 5: URL拼接逻辑验证")
    print("=" * 80)
    
    import os
    
    test_cases = [
        {
            "name": "本地上传 + FILES_URL已设置",
            "transfer_method": "local_file",
            "remote_url": "/files/test-id/file-preview?timestamp=123&nonce=test&sign=test",
            "url": "/files/test-id/file-preview?timestamp=123&nonce=test&sign=test",
            "files_url": "http://localhost:5001",
            "expected": "http://localhost:5001/files/test-id/file-preview?timestamp=123&nonce=test&sign=test"
        },
        {
            "name": "本地上传 + FILES_URL未设置",
            "transfer_method": "local_file",
            "remote_url": "/files/test-id/file-preview",
            "url": "/files/test-id/file-preview",
            "files_url": None,
            "expected": None  # 应该报错
        },
        {
            "name": "文件URL + 完整URL",
            "transfer_method": "remote_url",
            "remote_url": "https://example.com/files/test.pdf",
            "url": "https://example.com/files/test.pdf",
            "files_url": None,
            "expected": "https://example.com/files/test.pdf"  # 直接使用，不需要拼接
        },
        {
            "name": "文件URL + 相对路径 + FILES_URL已设置",
            "transfer_method": "remote_url",
            "remote_url": "/files/test-id/file-preview",
            "url": "/files/test-id/file-preview",
            "files_url": "http://localhost:5001",
            "expected": "http://localhost:5001/files/test-id/file-preview"
        },
    ]
    
    for case in test_cases:
        print(f"\n测试: {case['name']}")
        print(f"  transfer_method: {case['transfer_method']}")
        print(f"  remote_url: {case['remote_url']}")
        print(f"  FILES_URL: {case['files_url']}")
        
        # 设置/清除环境变量
        if case['files_url']:
            os.environ['FILES_URL'] = case['files_url']
        elif 'FILES_URL' in os.environ:
            del os.environ['FILES_URL']
        
        # 模拟URL选择逻辑
        transfer_method = case['transfer_method']
        remote_url = case['remote_url']
        url = case['url']
        
        if transfer_method == 'local_file':
            file_url = remote_url or url
        elif transfer_method == 'remote_url':
            file_url = remote_url or url
        else:
            file_url = remote_url or url
        
        print(f"  选择的URL: {file_url}")
        
        # 模拟URL拼接逻辑
        if file_url and not file_url.startswith(('http://', 'https://')):
            files_url = os.environ.get('FILES_URL', '').rstrip('/')
            if files_url:
                final_url = f"{files_url}/{file_url.lstrip('/')}"
                print(f"  拼接后的URL: {final_url}")
                if case['expected']:
                    assert final_url == case['expected'], f"期望 {case['expected']}, 实际 {final_url}"
                    print(f"  ✓ 通过")
                else:
                    print(f"  ⚠ 应该报错但没有")
            else:
                print(f"  ✗ 错误: FILES_URL未设置，应该报错")
                if case['expected'] is None:
                    print(f"  ✓ 通过（正确报错）")
        else:
            final_url = file_url
            print(f"  最终URL: {final_url}")
            if case['expected']:
                assert final_url == case['expected'], f"期望 {case['expected']}, 实际 {final_url}"
                print(f"  ✓ 通过")
    
    print("\n" + "=" * 80)
    print("URL拼接逻辑测试完成")
    print("=" * 80)


if __name__ == "__main__":
    print("开始本地测试 DocumentParsingTool")
    print(f"项目根目录: {project_root}")
    print()
    
    # 检查测试文件是否存在
    pdf_path = project_root / "tests" / "43类合同风险清单.pdf"
    if not pdf_path.exists():
        print(f"错误: 测试文件不存在: {pdf_path}")
        print("请确保测试PDF文件存在于 tests/ 目录下")
        sys.exit(1)
    
    # 运行测试
    # 注意：场景1、3和4需要实际的vLLM服务器，如果服务器不可用会失败
    # 场景2和5主要测试错误处理和URL拼接逻辑
    
    # 测试场景5：URL拼接逻辑（不需要vLLM服务器）
    test_url_construction_logic()
    
    # 测试场景2：未设置FILES_URL的情况（主要测试错误处理）
    test_local_file_without_files_url()
    
    # 如果需要测试实际的文件处理，取消下面的注释
    # 但需要确保vLLM服务器可用
    # test_local_file_upload()
    # test_remote_url()
    # test_direct_blob_access()
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)
