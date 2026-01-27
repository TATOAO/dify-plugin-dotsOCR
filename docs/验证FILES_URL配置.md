# 如何验证 FILES_URL 配置是否成功

## 方法1：实际测试（最直接）

### 步骤1：上传测试文件

1. 在 Dify 中创建一个新的工作流或应用
2. 添加一个文件输入节点
3. 上传一个测试文件（PDF 或图片）
   - 可以使用项目中的测试文件：`tests/43类合同风险清单.pdf`

### 步骤2：使用文档解析工具

1. 在工作流中添加 **"Document Parsing"** 工具节点
2. 将文件输入连接到工具节点
3. 配置工具参数：
   - **File**: 选择上传的文件
   - **Mode**: 选择解析模式（如 "Full Layout Analysis"）
   - **Max Concurrency**: 保持默认或设置为 2-5
4. 运行工作流

### 步骤3：检查结果

**✅ 配置成功的情况：**
- 工具节点执行成功
- 返回解析结果（JSON 格式的布局信息）
- 没有错误信息

**❌ 配置失败的情况：**
- 出现错误信息，例如：
  ```
  Error: Invalid file URL '/files/xxx/file-preview?xxx': 
  Request URL is missing an 'http://' or 'https://' protocol.
  ```
  或
  ```
  Error: Failed to download file from http://your-ip:port/files/xxx (Status 404/403/500)
  ```

## 方法2：检查错误信息

### 如果配置错误，会看到以下错误：

#### 错误1：FILES_URL 未设置或为空
```
Error: Invalid file URL '/files/xxx/file-preview?xxx': 
Request URL is missing an 'http://' or 'https://' protocol. 
Please configure 'Dify Files URL' in the plugin settings, 
or set the `FILES_URL` environment variable...
```

**解决方法：**
- 检查插件配置中的 "Dify Files URL" 是否已填写
- 确认填写的是完整的 URL（包含 `http://` 或 `https://`）

#### 错误2：URL 拼接错误或无法访问
```
Error: Failed to download file from http://your-ip:port/files/xxx (Status 404)
```

**可能原因：**
- IP 地址或端口不正确
- 服务器无法从插件访问（网络问题）
- 文件路径不正确

**解决方法：**
- 确认 IP 和端口是否正确
- 检查服务器防火墙设置
- 确认 Dify 服务是否正常运行

#### 错误3：网络连接问题
```
Error: Failed to download file from http://your-ip:port/files/xxx 
(Connection refused / Timeout)
```

**可能原因：**
- 服务器未启动
- 端口被防火墙阻止
- 网络不通

**解决方法：**
- 检查服务器是否运行
- 检查防火墙规则
- 测试网络连接

## 方法3：手动验证 URL 拼接

### 步骤1：获取文件相对路径

当上传文件后，Dify 会生成一个相对路径，例如：
```
/files/d2fd660c-4c26-4d77-a776-577ac5e65ab4/file-preview?timestamp=xxx&nonce=xxx&sign=xxx
```

### 步骤2：拼接完整 URL

假设你配置的 FILES_URL 是：`http://192.168.1.100:5001`

完整 URL 应该是：
```
http://192.168.1.100:5001/files/d2fd660c-4c26-4d77-a776-577ac5e65ab4/file-preview?timestamp=xxx&nonce=xxx&sign=xxx
```

### 步骤3：在浏览器中测试

1. 复制完整 URL
2. 在浏览器中打开
3. 如果能看到文件或下载文件，说明 URL 拼接正确
4. 如果出现 404/403/500 错误，说明配置有问题

## 方法4：查看日志

### 查看 Dify 日志

```bash
# 如果使用 Docker 部署
cd /home/lwt/Work/news_fin_dify/docker
docker-compose logs -f api

# 查看插件相关日志
docker-compose logs -f | grep -i "files_url\|file.*url\|document.*parsing"
```

### 查看插件日志

插件执行时的错误信息会显示在工作流的执行结果中，或者在 Dify 的日志中。

## 方法5：使用测试脚本（本地验证）

如果你有本地测试环境，可以使用测试脚本验证 URL 拼接逻辑：

```bash
cd /home/lwt/Work/dify-plugin-dotsOCR
source .venv/bin/activate
python tests/test_file_url_logic.py
```

## 快速验证清单

- [ ] 在 Dify 中上传一个测试文件
- [ ] 使用 Document Parsing 工具处理文件
- [ ] 检查是否返回解析结果
- [ ] 如果没有结果，查看错误信息
- [ ] 根据错误信息调整配置

## 常见问题排查

### Q1: 配置了但还是报错 "missing protocol"

**A:** 检查配置值是否包含 `http://` 或 `https://`，例如：
- ✅ 正确：`http://192.168.1.100:5001`
- ❌ 错误：`192.168.1.100:5001`

### Q2: 配置了但返回 404 错误

**A:** 可能的原因：
1. IP 地址或端口不正确
2. 服务器无法从插件访问（插件可能在 Docker 容器中，需要确保网络可达）
3. 文件路径不正确

**解决方法：**
- 确认 IP 和端口是否正确
- 如果插件在 Docker 中运行，可能需要使用 Docker 内部网络地址
- 检查服务器防火墙设置

### Q3: 配置了但返回 403 错误

**A:** 可能是权限问题：
- 检查文件访问权限
- 确认签名（sign）参数是否正确
- 检查 Dify 的文件访问配置

### Q4: 如何确认插件能访问到服务器？

**A:** 如果插件在 Docker 容器中运行，可能需要：
1. 使用 Docker 内部网络地址（如 `http://api:5001`）
2. 或者确保服务器可以从 Docker 网络访问

**测试方法：**
```bash
# 在插件容器中测试网络连接
docker-compose exec <plugin-container> curl http://your-ip:port
```

## 成功标志

如果看到以下情况，说明配置成功：

1. ✅ 工具节点执行成功
2. ✅ 返回解析结果（JSON 格式）
3. ✅ 没有错误信息
4. ✅ 文件内容被正确解析

## 下一步

如果验证成功，你可以：
1. 继续使用插件处理更多文件
2. 根据需求调整解析模式
3. 优化工作流配置

如果验证失败，请：
1. 检查错误信息
2. 根据错误信息调整配置
3. 参考本文档的"常见问题排查"部分
