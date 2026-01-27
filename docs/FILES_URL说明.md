# FILES_URL 说明文档

## 什么是 FILES_URL？

`FILES_URL` 是 Dify 服务器的**基础地址**，用于将文件的**相对路径**转换为**完整的可访问URL**。

## 为什么需要 FILES_URL？

### 问题场景

当用户在 Dify 中上传文件时，Dify 会：
1. 将文件存储到服务器
2. 生成一个**相对路径**的 URL，例如：
   ```
   /files/d2fd660c-4c26-4d77-a776-577ac5e65ab4/file-preview?timestamp=1769422228&nonce=xxx&sign=xxx
   ```

### 问题

这个相对路径**不能直接用于下载文件**，因为：
- ❌ 相对路径：`/files/xxx/file-preview?xxx` （缺少协议和域名）
- ✅ 完整URL：`http://your-dify-domain.com/files/xxx/file-preview?xxx` （可以访问）

### 解决方案

使用 `FILES_URL` 将相对路径拼接成完整URL：

```
FILES_URL = "http://your-dify-domain.com"
相对路径 = "/files/xxx/file-preview?xxx"
完整URL = "http://your-dify-domain.com/files/xxx/file-preview?xxx"
```

## 代码中的使用

在我们的插件代码中（`document_parsing.py`），处理流程如下：

```python
# 1. 获取文件的相对路径URL
file_url = "/files/xxx/file-preview?xxx"  # 相对路径

# 2. 检查是否是相对路径（不以 http:// 或 https:// 开头）
if not file_url.startswith(('http://', 'https://')):
    # 3. 获取 FILES_URL
    files_url = os.environ.get('FILES_URL', '')
    
    # 4. 拼接成完整URL
    full_url = f"{files_url}/{file_url.lstrip('/')}"
    # 结果: "http://your-dify-domain.com/files/xxx/file-preview?xxx"
    
    # 5. 使用完整URL下载文件
    response = requests.get(full_url)
```

## 如何设置 FILES_URL？

### 方法1：在插件配置中设置（推荐，最简单）

**这是最简单的方法**，无需修改 Dify 环境变量，直接在插件设置界面配置：

1. 在 Dify 中打开插件管理页面
2. 找到 "Dots.OCR" 插件
3. 在插件配置中找到 **"Dify Files URL"** 字段
4. 填入你的 Dify 访问地址，例如：
   - `http://localhost:5001`（本地开发）
   - `https://dify.example.com`（生产环境）
   - `http://192.168.1.100:5001`（内网部署）
5. 保存配置

**优点：**
- ✅ 无需修改 Dify 环境变量
- ✅ 每个插件可以独立配置
- ✅ 配置更灵活，易于管理
- ✅ 优先级最高，会优先使用

### 方法2：在 Dify 的 .env 文件中设置（适用于 Docker 部署）

如果你使用 Docker 部署 Dify，在 Dify 项目的 `.env` 文件中设置：

```bash
# 在 .env 文件中找到 FILES_URL 配置项
# Setting FILES_URL is required for file processing plugins.
#   - For https://example.com, use FILES_URL=https://example.com
#   - For http://example.com, use FILES_URL=http://example.com
FILES_URL=https://your-dify-domain.com  # 设置为你的实际访问地址

# INTERNAL_FILES_URL is used for plugin daemon communication within Docker network.
# Example: INTERNAL_FILES_URL=http://api:5001
INTERNAL_FILES_URL=http://api:5001  # Docker 内部网络地址
```

**重要说明：**
- **FILES_URL**：外部可访问的地址（用户和插件从外部访问时使用）
  - 如果使用 HTTPS：`FILES_URL=https://dify.example.com`
  - 如果使用 HTTP：`FILES_URL=http://dify.example.com:5001`
  - 如果使用 IP 访问：`FILES_URL=http://192.168.1.100:5001`
  
- **INTERNAL_FILES_URL**：Docker 内部网络地址（用于容器间通信）
  - 通常设置为：`INTERNAL_FILES_URL=http://api:5001`
  - 这是 Docker Compose 中 api 服务的内部网络地址

**设置步骤：**
1. 打开 Dify 项目的 `.env` 文件（通常在 `docker/.env`）
2. 找到 `FILES_URL=` 这一行
3. 设置为你的 Dify 实际访问地址，例如：
   ```bash
   FILES_URL=https://dify.yourcompany.com
   # 或者
   FILES_URL=http://localhost:5001  # 本地开发
   ```
4. 找到 `INTERNAL_FILES_URL=` 这一行
5. 设置为 Docker 内部地址：
   ```bash
   INTERNAL_FILES_URL=http://api:5001
   ```
6. 保存文件并重启 Dify 服务：
   ```bash
   docker-compose down
   docker-compose up -d
   ```

### 方法2：在 Docker Compose 中直接设置

如果不想修改 `.env` 文件，可以在 `docker-compose.yml` 中直接设置：

```yaml
services:
  api:
    environment:
      - FILES_URL=https://dify.example.com  # 外部访问地址
      - INTERNAL_FILES_URL=http://api:5001  # 内部网络地址
    # ... 其他配置
```

### 方法3：在 Kubernetes 部署中设置

在 Kubernetes 的 ConfigMap 或 Deployment 中设置：

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: dify-config
data:
  FILES_URL: "https://dify.example.com"
```

或者在 Deployment 中：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dify-api
spec:
  template:
    spec:
      containers:
      - name: api
        env:
        - name: FILES_URL
          value: "https://dify.example.com"
```

## 如何确定 FILES_URL 的值？

### 1. 查看 Dify 的访问地址

- **本地开发**：通常是 `http://localhost:5001` 或 `http://127.0.0.1:5001`
- **生产环境**：你的域名，例如 `https://dify.yourcompany.com`
- **内网部署**：内网IP和端口，例如 `http://192.168.1.100:5001`

### 2. 验证设置

设置后，可以通过以下方式验证：

```bash
# 在 Dify 服务器上执行
echo $FILES_URL

# 或者在 Python 中测试
python -c "import os; print(os.environ.get('FILES_URL', '未设置'))"
```

## 常见问题

### Q1: 为什么会出现 "Request URL is missing an 'http://' or 'https://' protocol" 错误？

**A:** 这是因为 `FILES_URL` 环境变量没有设置，导致无法将相对路径转换为完整URL。

**解决方案：** 按照上面的方法设置 `FILES_URL` 环境变量。

### Q2: FILES_URL 应该包含端口号吗？

**A:** 是的，如果 Dify 运行在非标准端口（如 5001），需要包含端口号：

```bash
# 标准HTTP端口（80）可以省略
FILES_URL=http://dify.example.com

# 非标准端口必须包含
FILES_URL=http://dify.example.com:5001
```

### Q3: 如果使用 HTTPS，需要设置什么？

**A:** 使用 `https://` 协议：

```bash
FILES_URL=https://dify.example.com
```

### Q4: 插件代码会从哪里获取 FILES_URL？

**A:** 代码会按以下**优先级顺序**尝试获取：

1. **插件配置中的 `files_url`**（最高优先级，推荐使用）
   - 在插件设置界面中配置的 "Dify Files URL"
   - 这是最简单、最灵活的方式
   
2. **环境变量** `FILES_URL`
   - Dify 服务器的环境变量
   - 适用于所有插件共享同一配置的场景
   
3. **Runtime 属性**
   - `runtime.files_url`
   - `runtime.FILES_URL`
   - `runtime.config.files_url` 或 `runtime.config.FILES_URL`

如果都获取不到，会报错提示在插件设置中配置或设置环境变量。

### Q5: FILES_URL 和 INTERNAL_FILES_URL 有什么区别？

**A:** 
- **FILES_URL**：外部可访问的地址
  - 用于：用户浏览器、外部插件、API 调用等从外部访问
  - 格式：`https://dify.example.com` 或 `http://dify.example.com:5001`
  
- **INTERNAL_FILES_URL**：Docker 内部网络地址
  - 用于：Docker 容器之间的内部通信（如插件守护进程）
  - 格式：`http://api:5001`（使用 Docker Compose 服务名）

**对于我们的插件：**
- 插件代码主要使用 **FILES_URL**（外部访问地址）
- **INTERNAL_FILES_URL** 是 Dify 内部使用的，插件通常不需要关心

### Q6: 本地上传和文件URL上传有什么区别？

**A:** 
- **本地上传** (`transfer_method="local_file"`)：
  - 文件存储在 Dify 服务器上
  - URL 通常是相对路径，**必须**使用 `FILES_URL` 拼接
  
- **文件URL上传** (`transfer_method="remote_url"`)：
  - 文件来自外部URL
  - URL 可能已经是完整URL（如 `https://example.com/file.pdf`），不需要拼接
  - 如果也是相对路径，同样需要 `FILES_URL` 拼接

## 示例

### 示例1：本地开发环境（Docker）

在 `.env` 文件中设置：

```bash
# 外部访问地址（浏览器访问）
FILES_URL=http://localhost:5001

# Docker 内部网络地址
INTERNAL_FILES_URL=http://api:5001
```

### 示例2：生产环境（HTTPS）

在 `.env` 文件中设置：

```bash
# 外部访问地址（用户和插件访问）
FILES_URL=https://dify.yourcompany.com

# Docker 内部网络地址
INTERNAL_FILES_URL=http://api:5001
```

### 示例3：内网部署

在 `.env` 文件中设置：

```bash
# 外部访问地址（内网IP）
FILES_URL=http://192.168.1.100:5001

# Docker 内部网络地址
INTERNAL_FILES_URL=http://api:5001
```

### 示例4：使用域名但非标准端口

在 `.env` 文件中设置：

```bash
# 外部访问地址（包含端口）
FILES_URL=http://dify.example.com:8080

# Docker 内部网络地址
INTERNAL_FILES_URL=http://api:5001
```

## 测试

可以使用我们提供的测试脚本验证 URL 拼接逻辑：

```bash
cd /home/lwt/Work/dify-plugin-dotsOCR
source .venv/bin/activate
python tests/test_file_url_logic.py
```

## 根据你的配置快速设置

根据你提供的 Dify 配置，在 `.env` 文件中找到以下配置项：

```bash
# 第 984 行附近
FILES_URL=  # 当前为空，需要设置

# 第 987 行附近  
INTERNAL_FILES_URL=  # 当前为空，需要设置
```

**设置方法：**

1. **确定你的 Dify 访问地址**
   - 如果通过浏览器访问：`http://localhost:5001` → 设置 `FILES_URL=http://localhost:5001`
   - 如果有域名：`https://dify.example.com` → 设置 `FILES_URL=https://dify.example.com`
   - 如果是内网IP：`http://192.168.1.100:5001` → 设置 `FILES_URL=http://192.168.1.100:5001`

2. **编辑 `.env` 文件**
   ```bash
   # 在 docker/.env 文件中
   FILES_URL=http://localhost:5001  # 替换为你的实际地址
   INTERNAL_FILES_URL=http://api:5001  # Docker 内部地址，通常保持不变
   ```

3. **重启 Dify 服务**
   ```bash
   cd docker
   docker-compose down
   docker-compose up -d
   ```

4. **验证设置**
   ```bash
   # 检查环境变量是否生效
   docker-compose exec api env | grep FILES_URL
   ```

## 总结

- **FILES_URL** = Dify 服务器的**外部访问地址**（协议 + 域名/IP + 端口）
  - 用于：用户浏览器、外部插件访问文件
  - 格式：`http://domain:port` 或 `https://domain:port`
  - **必须设置**，否则插件无法下载文件

- **INTERNAL_FILES_URL** = Docker **内部网络地址**
  - 用于：Docker 容器间通信
  - 格式：`http://api:5001`（使用服务名）
  - 通常设置为：`http://api:5001`

- **作用**：将文件的相对路径转换为完整的可访问URL

- **设置位置**：Dify 项目的 `.env` 文件（通常在 `docker/.env`）

设置好 `FILES_URL` 后，插件就能正确下载和处理用户上传的文件了！
