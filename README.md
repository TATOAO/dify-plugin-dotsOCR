# Dify Plugin - Dots.OCR 文档解析插件

这是一个为 Dify 平台开发的文档解析插件，集成了 `dots.ocr` 多模态视觉模型，实现对 PDF 和图像文档的智能 OCR 识别和布局分析。

## 功能特性

- **智能布局识别**：识别文档结构（标题、段落、表格、图片等）。
- **多格式支持**：支持 PDF、JPEG、PNG、WEBP 等常见文档格式。
- **高性能并行处理**：支持多页 PDF 并行处理。
- **结构化输出**：输出包含布局信息、类别、坐标等结构化数据。

## 安装

1. 在 Dify 插件管理页面中上传此插件包。
2. 配置插件设置（服务器 IP、端口等）。

## 配置参数

- `server_ip`: vLLM 服务器 IP 地址。
- `server_port`: vLLM 服务器端口（默认 8001）。
- `protocol`: 协议类型（http/https）。
- `model_name`: 模型名称（默认 model）。
- `timeout`: 请求超时时间（默认 3600 秒）。

## 工具使用

### document_parsing
解析 PDF 或图像文件。

**输入参数：**
- `file`: 要解析的 PDF 或图像文件。
- `prompt_mode`: 解析模式。
  - `Full Layout Analysis`: 完整布局分析。
  - `Layout Only`: 仅布局识别。
  - `OCR Only`: 纯 OCR。
- `max_concurrency`: PDF 多页处理的最大并发数（默认 20）。

## 开发与构建

### 1. 安装 Dify CLI

- **Linux**: 从 Dify GitHub releases 页面下载对应版本的二进制文件并安装。
  ```bash
  chmod +x dify-plugin-linux-amd64
  mv dify-plugin-linux-amd64 dify
  sudo mv dify /usr/local/bin/
  ```
- **Mac**: `brew tap langgenius/dify && brew install dify`

### 2. 环境配置

1. 安装 Python 依赖：
   ```bash
   uv pip install -r requirements.txt
   ```
2. 配置调试环境变量（复制 `.env.example` 并填入 Dify 实例的调试信息）：
   ```bash
   cp .env.example .env
   # 编辑 .env 文件
   # INSTALL_METHOD=remote
   # REMOTE_INSTALL_HOST=...
   # REMOTE_INSTALL_KEY=...
   ```

### 3. 调试运行

在项目根目录下运行插件，它将以调试模式连接到 Dify 实例：
```bash
python3 -m main
```

### 4. 测试

运行单元测试：
```bash
python3 -m unittest tests/test_client.py
```

### 5. 打包

打包插件供 Dify Marketplace 或手动安装：
```bash
dify plugin package ./
```
生成的文件为 `plugin.difypkg`。

## 参考资源
- [dots.ocr GitHub](https://github.com/rednote-hilab/dots.ocr)
