# Daybreak

破晓 — 安全评估多 Agent 工作平台

单文件二进制，无需安装 Python 或其他依赖。

## 下载

从 [Releases](https://github.com/Linyisheng1/daybreak/releases) 下载最新版本。

## 快速开始

```bash
# 1. 赋予执行权限
chmod +x daybreak

# 2. 创建配置文件
# 参考 .daybreak/config.json.example 创建 config.json

# 3. 运行
./daybreak
```

## 要求

- Linux x86_64
- Docker（沙箱功能需要）

## 配置

参考 `.daybreak/config.json.example`，在同目录创建 `config.json`，填入以下必要信息：
- `api_key`: OpenAI / Anthropic API Key
- `database.url`: PostgreSQL 连接地址
- `jwt.secret`: JWT 签名密钥（建议随机生成）
- `encryption_key`: 数据加密密钥（建议随机生成）

## 构建

如果需要从源码构建，需在 Python 3.13 Docker 容器中执行：

```bash
python build_binary.py
```
