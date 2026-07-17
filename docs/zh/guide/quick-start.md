---
title: 快速开始
editLink: true
---

# 快速开始

推荐部署方式由宿主机上的 `daybreak.bin`、Compose 管理的 PostgreSQL，以及由 Daybreak 动态创建的沙箱容器组成。用户无需安装 Python、Node.js 或编译前端。

## 最短部署路径

在一台 `x86_64/amd64` Linux 机器上复制执行：

```bash
curl -L -o daybreak-linux-amd64-0.2.0.tar.gz \
  https://github.com/Linyisheng1/daybreak/releases/download/v0.2.0/daybreak-linux-amd64-0.2.0.tar.gz
tar -xzf daybreak-linux-amd64-0.2.0.tar.gz
cd daybreak-linux-amd64-0.2.0

./daybreak doctor
./daybreak up
```

启动完成后访问：

```text
http://服务器IP:8000
```

默认登录账号为 admin@daybreak.local，默认密码为 admin。也可以在 .env 中查看：

```bash
grep -E "DAYBREAK_ADMIN_EMAIL|DAYBREAK_ADMIN_PASSWORD" .env
```

如果 `doctor` 或 `up` 提示环境问题，按提示使用：

```bash
./daybreak install-docker     # Docker 未安装
./daybreak fix-permissions    # 当前用户无 Docker 权限，执行后重新登录
./daybreak registry-login     # 私有 GHCR 镜像拉取失败
./daybreak status             # 查看运行状态
./daybreak logs               # 查看日志
```

## 支持环境

| 项目 | 要求 |
| --- | --- |
| 操作系统 | Ubuntu、Debian、CentOS、RHEL 或兼容 Linux |
| 架构 | `x86_64/amd64` |
| 容器运行时 | Docker Engine，Docker Compose v2 |
| 权限 | 当前用户能够读写 Docker Socket |
| 网络 | 能访问 Docker Hub、GHCR 和模型 API |
| 建议资源 | 4 核 CPU、8 GB 内存、20 GB 可用磁盘 |

当前沙箱镜像仅支持 amd64。Windows 用户可以在启用了 Docker 集成的 WSL2 Linux 发行版中部署，但 WSL2 不是必需条件。

## 准备发行包

解压发行包后应看到：

```text
daybreak.bin
daybreak
daybreak-defaults/
.env.example
deploy/docker-compose.dependencies.yml
```

进入安装目录并授予执行权限：

```bash
chmod +x daybreak daybreak.bin
```

## 部署前检查

```bash
./daybreak doctor
```

该命令只检查环境，不修改系统。它会检查 Linux 架构、Docker CLI、Docker API、Compose v2、Docker Socket 权限和二进制文件。

### Docker 未安装

可以使用启动器调用 Docker 官方安装脚本：

```bash
./daybreak install-docker
```

该方式适合快速部署和测试环境。生产环境建议按照 Docker 官方文档配置 Ubuntu/Debian APT 仓库或 CentOS/RHEL RPM 仓库。

### Docker 权限不足

```bash
./daybreak fix-permissions
```

命令会将当前用户加入 `docker` 用户组。执行后需要退出当前 Linux 会话并重新登录，再运行：

```bash
./daybreak doctor
```

不要将 Docker API 以未加密的 `2375` 端口暴露到网络。Daybreak 的本机部署默认使用 `/var/run/docker.sock`。

### GHCR 镜像没有拉取权限

公开镜像不需要登录。如果仓库的 GHCR Package 是私有状态，运行：

```bash
./daybreak registry-login
```

按提示输入 GitHub 用户名和具备 `read:packages` 权限的 Token。Token 通过标准输入交给 Docker，不会写入 `.env`。

## 首次启动

```bash
./daybreak up
```

首次启动会自动：

1. 创建权限为 `600` 的 `.env`。
2. 写入默认管理员账号密码，并生成数据库密码和加密密钥。
3. 拉取 PostgreSQL 与沙箱镜像。
4. 启动并检查 PostgreSQL。
5. 将 PostgreSQL 实际密码同步为 `.env` 中的密码。
6. 启动 `daybreak.bin`。
7. 初始化 `.daybreak/config.json` 和 Agent 文件。
8. 在系统中登记默认沙箱镜像。
9. 等待 HTTP 健康检查通过。

完成后访问：

```text
http://127.0.0.1:8000
```

默认管理员账号和密码为：

```dotenv
DAYBREAK_ADMIN_EMAIL=admin@daybreak.local
DAYBREAK_ADMIN_PASSWORD=admin
```
镜像源默认使用国内加速：PostgreSQL 为 docker.m.daocloud.io/postgres:16-alpine，沙箱为 ghcr.nju.edu.cn/linyisheng1/daybreak-sandbox:latest。如需切回官方源，编辑 .env 中的 DAYBREAK_POSTGRES_IMAGE 和 DAYBREAK_SANDBOX_IMAGE 后执行 ./daybreak restart。

## 配置模型

编辑 `.env`：

```dotenv
DAYBREAK_MODEL_BASE_URL=https://api.example.com/v1
DAYBREAK_MODEL_API_KEY=replace-with-your-api-key
DAYBREAK_MODEL_NAME=your-model-name
```

然后重启：

```bash
./daybreak restart
```

`.env` 是部署参数的唯一来源。启动时，相同的 `DAYBREAK_DB_PASSWORD` 会同时传给 PostgreSQL 和 Daybreak，模型配置也会覆盖到所有默认 Agent。

## 管理命令

```bash
./daybreak status
./daybreak logs
./daybreak restart
./daybreak down
```

`down` 会停止应用和 PostgreSQL，但不会删除 `daybreak-pgdata` 数据卷。不要使用 `docker compose down -v`，除非确定要永久删除数据库。

## 数据位置

| 数据 | 位置 |
| --- | --- |
| 部署参数和密钥 | `.env` |
| Daybreak 配置和 Agent 文件 | `.daybreak/` |
| 应用日志 | `.daybreak/app.log` |
| PostgreSQL 数据 | Docker 卷 `daybreak-pgdata` |
| 报告 | `reports/` |
| 沙箱 | Daybreak 动态创建的 Docker 容器 |

升级前应备份 `.env`、`.daybreak/`、`reports/` 和 PostgreSQL 数据卷。替换 `daybreak.bin` 不会自动删除这些数据。

## 常见问题

### `Cannot connect to the Docker daemon`

确认 Docker 已启动，再执行 `./daybreak fix-permissions` 并重新登录系统。

### `permission denied /var/run/docker.sock`

当前会话尚未获得 `docker` 用户组权限。退出 SSH、桌面或终端登录会话后重新登录，不要通过开放 `2375` 端口绕过权限问题。

### `unauthorized` 或 `denied` 拉取失败

确认 GHCR Package 为公开状态，或者执行 `./daybreak registry-login`。同时检查 Token 是否具备 `read:packages` 权限。

### PostgreSQL 启动失败

执行 `./daybreak logs`。常见原因是 `5432` 端口被占用、磁盘空间不足或旧数据卷损坏。可以在 `.env` 中修改 `DAYBREAK_DB_PORT`，但不要直接修改容器内密码。

### 页面可以打开，但沙箱不可用

执行 `./daybreak status`，确认沙箱镜像为 `ready`，并确认当前用户可以访问 Docker Socket。沙箱镜像由 Compose 拉取，但具体沙箱容器由 Daybreak 根据项目动态创建。

## 下一步

部署完成并验证模型连接后，按照[首次使用](./first-use)创建沙箱容器和工作项目。
