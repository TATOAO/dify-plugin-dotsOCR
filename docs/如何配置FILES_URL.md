# 如何配置 FILES_URL - 详细指南

## ⚠️ 重要：不能随便设置！

`FILES_URL` **必须**设置为你的 Dify 实例的**实际访问地址**，不能随便填写。如果设置错误，插件将无法访问文件。

## 如何确定正确的 FILES_URL 值？

### 方法1：查看浏览器地址栏（最简单）

1. 打开浏览器，访问你的 Dify 实例
2. 查看浏览器地址栏中的 URL
3. 复制**协议 + 域名/IP + 端口**部分（不包括路径）

**示例：**
- 如果浏览器显示：`http://localhost:5001/chat` 
  → FILES_URL 应该设置为：`http://localhost:5001`
  
- 如果浏览器显示：`https://dify.example.com/workflows`
  → FILES_URL 应该设置为：`https://dify.example.com`
  
- 如果浏览器显示：`http://192.168.1.100:5001/apps`
  → FILES_URL 应该设置为：`http://192.168.1.100:5001`

### 方法2：查看 Docker Compose 配置

如果你使用 Docker 部署，可以查看 `docker-compose.yml` 文件：

```bash
cd /home/lwt/Work/news_fin_dify/docker
cat docker-compose.yml | grep -A 5 "ports:"
```

查看端口映射，例如：
- `"5001:5001"` → 如果通过 `localhost:5001` 访问，设置为 `http://localhost:5001`
- `"80:5001"` → 如果通过 `http://localhost` 访问，设置为 `http://localhost`

### 方法3：查看 Nginx 配置（如果使用反向代理）

如果使用 Nginx 反向代理，查看 Nginx 配置中的 `server_name`：

```bash
# 查看 Nginx 配置
cat nginx.conf | grep server_name
```

## 常见场景配置示例

### 场景1：本地开发（Docker）

**访问方式：** `http://localhost:5001`

**配置：**
```yaml
# 在插件配置中
Dify Files URL: http://localhost:5001
```

### 场景2：本地开发（非标准端口）

**访问方式：** `http://localhost:8080`

**配置：**
```yaml
# 在插件配置中
Dify Files URL: http://localhost:8080
```

### 场景3：生产环境（HTTPS + 域名）

**访问方式：** `https://dify.yourcompany.com`

**配置：**
```yaml
# 在插件配置中
Dify Files URL: https://dify.yourcompany.com
```

### 场景4：内网部署（IP地址）

**访问方式：** `http://192.168.1.100:5001`

**配置：**
```yaml
# 在插件配置中
Dify Files URL: http://192.168.1.100:5001
```

### 场景5：使用反向代理（Nginx）

**访问方式：** `https://dify.example.com`（通过 Nginx 代理到内部 `http://api:5001`）

**配置：**
```yaml
# 在插件配置中（使用外部访问地址）
Dify Files URL: https://dify.example.com
```

## 配置步骤

### 步骤1：确定你的 Dify 访问地址

打开浏览器，访问你的 Dify，记录地址栏中的 URL。

### 步骤2：在插件配置中设置

1. 在 Dify 中打开 **插件管理** 页面
2. 找到 **"Dots.OCR"** 插件
3. 点击 **配置** 或 **设置**
4. 找到 **"Dify Files URL"** 字段
5. 填入你在步骤1中确定的地址（只包含协议+域名/IP+端口，不包括路径）
6. 点击 **保存**

### 步骤3：验证配置

1. 上传一个测试文件
2. 运行文档解析工具
3. 如果成功，说明配置正确
4. 如果失败，检查错误信息，确认地址是否正确

## 常见错误

### ❌ 错误1：包含路径

```
错误：https://dify.example.com/apps
正确：https://dify.example.com
```

### ❌ 错误2：缺少协议

```
错误：dify.example.com
正确：https://dify.example.com
```

### ❌ 错误3：使用内部 Docker 地址

```
错误：http://api:5001  （这是 Docker 内部地址，插件无法访问）
正确：http://localhost:5001  （外部访问地址）
```

### ❌ 错误4：端口不匹配

```
错误：http://localhost:5001  （实际访问是 8080 端口）
正确：http://localhost:8080
```

## 验证配置是否正确

配置后，可以通过以下方式验证：

### 方法1：测试文件上传

1. 上传一个 PDF 文件
2. 使用文档解析工具处理
3. 如果成功，说明配置正确

### 方法2：查看错误信息

如果配置错误，会看到类似错误：
```
Error: Invalid file URL '/files/xxx/file-preview?xxx': 
Request URL is missing an 'http://' or 'https://' protocol.
```

### 方法3：检查拼接后的URL

在代码中，相对路径会被拼接成：
```
FILES_URL + 相对路径 = 完整URL
```

例如：
- FILES_URL: `http://localhost:5001`
- 相对路径: `/files/xxx/file-preview?xxx`
- 完整URL: `http://localhost:5001/files/xxx/file-preview?xxx`

你可以在浏览器中直接访问这个完整URL，如果能下载文件，说明配置正确。

## 根据你的情况配置

根据你提供的 `.env` 文件，你的 Dify 部署在 Docker 中。

**请告诉我：**
1. 你通过什么地址访问 Dify？（例如：`http://localhost:5001`）
2. 是本地开发还是生产环境？
3. 是否使用了反向代理（Nginx）？

**然后我可以帮你确定正确的配置值。**

## 快速检查清单

- [ ] 打开浏览器，访问 Dify
- [ ] 查看地址栏中的 URL
- [ ] 复制协议 + 域名/IP + 端口部分
- [ ] 在插件配置中填入这个值
- [ ] 保存配置
- [ ] 测试文件上传和解析

## 总结

1. **FILES_URL 不能随便设置**，必须是你的 Dify 实际访问地址
2. **最简单的方法**：查看浏览器地址栏，复制协议+域名/IP+端口
3. **在插件配置中设置**，无需修改 Dify 环境变量
4. **验证配置**：上传文件测试，如果成功说明配置正确
