# 破晓 Daybreak - Docker 一键部署

## 快速启动

```bash
cd /home/AI/daybreak
docker compose -f docker/docker-compose.yml up -d
```

启动后浏览器访问 **http://127.0.0.1:8000**

- 账号: `admin@daybreak.local`
- 密码: `admin`

## 常用命令

```bash
# 启动
docker compose -f docker/docker-compose.yml up -d

# 查看日志
docker compose -f docker/docker-compose.yml logs -f app

# 停止
docker compose -f docker/docker-compose.yml down

# 停止并删除数据(谨慎!)
docker compose -f docker/docker-compose.yml down -v

# 重新构建(修改代码后)
docker compose -f docker/docker-compose.yml up -d --build
```

## 数据持久化

Docker Compose 使用命名卷持久化以下数据:

| 卷名 | 用途 |
|------|------|
| `daybreak-config` | 配置文件 (.daybreak/) |
| `daybreak-pgdata` | PostgreSQL 数据 |
| `daybreak-reports` | 生成的报告文件 |

## 沙箱功能

Docker socket 已挂载到容器中，支持沙箱容器管理。
宿主机需要运行 Docker 服务。

## 端口

| 端口 | 服务 |
|------|------|
| 8000 | 破晓 Web 应用 |
| 5432 | PostgreSQL |
