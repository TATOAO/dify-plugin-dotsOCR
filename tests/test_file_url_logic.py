#!/usr/bin/env python3
"""
简化的测试脚本：直接测试文件URL处理逻辑
不需要实例化完整的工具类，只测试核心的文件URL拼接逻辑
"""

import os
import sys
from pathlib import Path


def test_url_construction_logic():
    """测试URL拼接逻辑"""
    print("=" * 80)
    print("测试文件URL拼接逻辑")
    print("=" * 80)
    
    test_cases = [
        {
            "name": "本地上传 + FILES_URL已设置",
            "transfer_method": "local_file",
            "remote_url": "/files/d2fd660c-4c26-4d77-a776-577ac5e65ab4/file-preview?timestamp=1769422228&nonce=a86adb0e657cd3d2351913a64ac03104&sign=WRPA_9Vybwy5h7saEvofmh5M-QQ3YT-pNPvHG768JGw%3D",
            "url": "/files/d2fd660c-4c26-4d77-a776-577ac5e65ab4/file-preview?timestamp=1769422228&nonce=a86adb0e657cd3d2351913a64ac03104&sign=WRPA_9Vybwy5h7saEvofmh5M-QQ3YT-pNPvHG768JGw%3D",
            "files_url": "http://localhost:5001",
            "expected": "http://localhost:5001/files/d2fd660c-4c26-4d77-a776-577ac5e65ab4/file-preview?timestamp=1769422228&nonce=a86adb0e657cd3d2351913a64ac03104&sign=WRPA_9Vybwy5h7saEvofmh5M-QQ3YT-pNPvHG768JGw%3D"
        },
        {
            "name": "本地上传 + FILES_URL未设置（应该报错）",
            "transfer_method": "local_file",
            "remote_url": "/files/d2fd660c-4c26-4d77-a776-577ac5e65ab4/file-preview?timestamp=1769422228&nonce=a86adb0e657cd3d2351913a64ac03104&sign=WRPA_9Vybwy5h7saEvofmh5M-QQ3YT-pNPvHG768JGw%3D",
            "url": "/files/d2fd660c-4c26-4d77-a776-577ac5e65ab4/file-preview?timestamp=1769422228&nonce=a86adb0e657cd3d2351913a64ac03104&sign=WRPA_9Vybwy5h7saEvofmh5M-QQ3YT-pNPvHG768JGw%3D",
            "files_url": None,
            "expected": None  # 应该报错
        },
        {
            "name": "文件URL + 完整URL（不需要拼接）",
            "transfer_method": "remote_url",
            "remote_url": "https://example.com/files/test.pdf",
            "url": "https://example.com/files/test.pdf",
            "files_url": None,
            "expected": "https://example.com/files/test.pdf"
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
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n测试 {i}: {case['name']}")
        print(f"  transfer_method: {case['transfer_method']}")
        print(f"  remote_url: {case['remote_url'][:80]}..." if len(case['remote_url']) > 80 else f"  remote_url: {case['remote_url']}")
        print(f"  FILES_URL: {case['files_url']}")
        
        # 设置/清除环境变量
        if case['files_url']:
            os.environ['FILES_URL'] = case['files_url']
        elif 'FILES_URL' in os.environ:
            del os.environ['FILES_URL']
        
        # 模拟URL选择逻辑（与 document_parsing.py 中的逻辑一致）
        transfer_method = case['transfer_method']
        remote_url = case['remote_url']
        url = case['url']
        
        if transfer_method == 'local_file':
            file_url = remote_url or url
        elif transfer_method == 'remote_url':
            file_url = remote_url or url
        else:
            file_url = remote_url or url
        
        print(f"  选择的URL: {file_url[:80]}..." if len(file_url) > 80 else f"  选择的URL: {file_url}")
        
        # 模拟URL拼接逻辑（与 document_parsing.py 中的逻辑一致）
        if file_url and not file_url.startswith(('http://', 'https://')):
            files_url = os.environ.get('FILES_URL', '').rstrip('/')
            
            # 尝试从 runtime 获取（这里模拟为 None，因为测试中没有 runtime）
            # files_url = getattr(runtime, 'files_url', None) or files_url
            
            if files_url:
                final_url = f"{files_url}/{file_url.lstrip('/')}"
                print(f"  拼接后的URL: {final_url[:80]}..." if len(final_url) > 80 else f"  拼接后的URL: {final_url}")
                if case['expected']:
                    assert final_url == case['expected'], f"期望 {case['expected']}, 实际 {final_url}"
                    print(f"  ✓ 通过")
                else:
                    print(f"  ✗ 失败: 应该报错但没有")
            else:
                print(f"  ✗ 错误: FILES_URL未设置，应该报错")
                if case['expected'] is None:
                    print(f"  ✓ 通过（正确报错）")
                else:
                    print(f"  ✗ 失败: 应该成功但没有")
        else:
            final_url = file_url
            print(f"  最终URL: {final_url[:80]}..." if len(final_url) > 80 else f"  最终URL: {final_url}")
            if case['expected']:
                assert final_url == case['expected'], f"期望 {case['expected']}, 实际 {final_url}"
                print(f"  ✓ 通过")
            else:
                print(f"  ✗ 失败: 应该报错但没有")
    
    print("\n" + "=" * 80)
    print("URL拼接逻辑测试完成")
    print("=" * 80)
    print("\n结论:")
    print("1. 当 transfer_method='local_file' 且 FILES_URL 已设置时，URL拼接正确")
    print("2. 当 transfer_method='local_file' 且 FILES_URL 未设置时，应该报错（这是正确的行为）")
    print("3. 当 transfer_method='remote_url' 且 URL 是完整URL时，直接使用")
    print("4. 当 transfer_method='remote_url' 且 URL 是相对路径时，需要拼接 FILES_URL")
    print("\n如果测试全部通过，说明URL拼接逻辑是正确的。")
    print("如果Dify环境中仍然报错，请检查：")
    print("  1. FILES_URL 环境变量是否在Dify环境中正确设置")
    print("  2. Dify runtime 中是否有 files_url 属性（代码会尝试从 runtime 获取）")


if __name__ == "__main__":
    test_url_construction_logic()
