# 代理检测工具

一个功能强大的 Windows 代理检测工具，支持批量检测、实时统计和结果导出。

## 功能特性

✅ **批量检测** - 支持同时检测多个代理  
✅ **多协议支持** - 支持 HTTP、HTTPS、SOCKS5  
✅ **并发检测** - 可调节并发数，快速完成检测  
✅ **实时统计** - 成功率、平均延迟、最快/最慢代理  
✅ **结果排序** - 按延迟自动排序  
✅ **导入导出** - 支持文件导入和结果导出  
✅ **友好界面** - 简洁的 GUI 界面

## 安装

### 环境要求

- Python 3.7+
- Windows 7/10/11

### 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### 方式一: GUI 图形界面 (推荐)

**Windows 用户:**

双击 `start.bat` 即可启动

**或手动启动:**

```bash
python proxy_checker.py
```

### 方式二: 命令行版本

适合自动化脚本和高级用户:

```bash
# 基本用法
python proxy_checker_cli.py -i proxies.txt

# 指定并发和超时
python proxy_checker_cli.py -i proxies.txt -c 20 -t 15

# 导出为 CSV
python proxy_checker_cli.py -i proxies.txt -o result.csv --format csv

# 详细输出
python proxy_checker_cli.py -i proxies.txt -v

# 查看所有选项
python proxy_checker_cli.py --help
```

**命令行参数:**

- `-i, --input`: 代理列表文件 (必需)
- `-o, --output`: 输出文件 (可选)
- `--format`: 输出格式 (txt/csv/json, 默认 txt)
- `-u, --url`: 测试 URL (默认 http://www.google.com)
- `-t, --timeout`: 超时时间/秒 (默认 10)
- `-c, --concurrency`: 并发数 (默认 10)
- `-v, --verbose`: 详细输出

### 代理格式

支持以下格式：

```
# 默认 HTTP 协议
192.168.1.1:8080

# 指定协议
http://192.168.1.2:8080
https://192.168.1.3:8080
socks5://192.168.1.4:1080

# 带账号密码
username:password@192.168.1.5:8080
http://user:pass@192.168.1.6:8080
socks5://admin:123456@192.168.1.7:1080

# 注释行(以 # 开头)
# 这是注释
```

### 配置选项

- **测试 URL**: 用于测试代理的目标网址(默认: http://www.google.com)
- **超时**: 单个代理的超时时间，单位秒(默认: 10s)
- **并发数**: 同时检测的代理数量(默认: 10)

### 操作流程

1. **导入代理列表**
   - 点击「📁 导入文件」从文本文件导入
   - 或直接在输入框中粘贴代理列表

2. **配置参数**
   - 设置测试 URL(可选)
   - 调整超时时间(可选)
   - 调整并发数(可选)

3. **开始检测**
   - 点击「🚀 开始检测」
   - 实时查看进度和结果

4. **导出结果**
   - 点击「💾 导出结果」
   - 保存为 TXT 或 CSV 格式

## 统计信息

检测完成后会显示：

- **总计**: 检测的代理总数
- **成功**: 可用代理数量
- **失败**: 不可用代理数量
- **成功率**: 可用代理百分比
- **平均延迟**: 所有可用代理的平均响应时间
- **最快/最慢**: 延迟最低和最高的代理

## 结果说明

| 状态 | 说明 |
|------|------|
| ✓ 成功 | 代理可用，能正常连接 |
| ✗ 失败 | 代理不可用，连接失败 |
| ⏱ 超时 | 代理响应超时 |

## 打包为 EXE

使用 PyInstaller 打包为单文件 EXE：

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name="代理检测工具" --icon=icon.ico proxy_checker.py
```

生成的 EXE 在 `dist/` 目录下。

## 常见问题

### Q: 为什么有些代理显示超时？

A: 可能原因：
- 代理服务器响应慢
- 网络不稳定
- 超时时间设置太短

**解决方法**: 增加超时时间(如 15-30秒)

### Q: 检测速度慢怎么办？

A: 增加并发数(如 20-50)，但注意：
- 并发过高可能导致网络拥塞
- 某些代理服务器可能限制并发连接

### Q: 支持需要认证的代理吗？

A: 当前版本不支持，代理格式需要包含认证信息：
```
http://username:password@192.168.1.1:8080
```

如需此功能，请修改代码中的 `check_proxy` 方法。

## 技术栈

- **GUI**: tkinter (Python 自带)
- **异步**: asyncio + aiohttp
- **多线程**: threading

## 许可证

MIT License

## 更新日志

### v1.0 (2026-02-23)
- ✨ 初始版本
- ✅ 支持批量检测
- ✅ 实时统计
- ✅ 结果导出
