#!/bin/bash
# 破晓 Daybreak Startup Script
# Copies pre-configured files into the project and starts the server.
# Usage: bash start.sh

set -e

PERSIST_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="/home/AI/Z3r0"

echo "=========================================="
echo "  破晓 Daybreak 安全评估平台 - 启动脚本"
echo "=========================================="
echo ""

# 1. Copy config.json
echo "[1/8] 复制配置文件..."
mkdir -p "$PROJECT_DIR/.daybreak"
cp "$PERSIST_DIR/config.json" "$PROJECT_DIR/.daybreak/config.json"
echo "  ✓ config.json 已复制"

# 2. Copy dist-app (frontend build - Chinese translated)
echo "[2/8] 复制前端构建文件 (中文版)..."
rm -rf "$PROJECT_DIR/web/dist-app"
cp -r "$PERSIST_DIR/dist-app" "$PROJECT_DIR/web/dist-app"
echo "  ✓ dist-app 已复制"

# 2a. Copy dist-landing (landing page build)
if [ -d "$PERSIST_DIR/dist-landing" ]; then
    echo "[2a/8] 复制 Landing 页面构建文件..."
    rm -rf "$PROJECT_DIR/web/dist-landing"
    cp -r "$PERSIST_DIR/dist-landing" "$PROJECT_DIR/web/dist-landing"
    echo "  ✓ dist-landing 已复制"
fi

# 2b. Copy translated source files (for rebuild if needed)
echo "[2b/8] 复制中文翻译源文件..."
SRC_BASE="$PERSIST_DIR/web-src"

# Helper: copy file to matching path under project web/src/
copy_src() {
    local src="$SRC_BASE/$1"
    local dst="$PROJECT_DIR/web/src/$1"
    if [ -f "$src" ]; then
        mkdir -p "$(dirname "$dst")"
        cp "$src" "$dst"
    fi
}

# Core shared
copy_src "shared/lib/uiText.ts"
copy_src "shared/lib/labels.ts"
copy_src "shared/lib/date.ts"
copy_src "shared/components/ResourcePageShell.tsx"
copy_src "shared/components/ResourceCells.tsx"
copy_src "shared/api/feedback.ts"
copy_src "main.tsx"

# Layouts & Auth
copy_src "app/layouts/AdminLayout.tsx"
copy_src "features/auth/LoginPage.tsx"

# System pages
copy_src "features/system-users/SystemUsersPage.tsx"
copy_src "features/system-users/UserFormModal.tsx"
copy_src "features/hosts/HostsPage.tsx"
copy_src "features/hosts/HostFormModal.tsx"
copy_src "features/egress-proxies/EgressProxiesPage.tsx"
copy_src "features/egress-proxies/EgressProxyFormModal.tsx"
copy_src "features/sandbox-images/SandboxImagesPage.tsx"
copy_src "features/sandbox-images/SandboxImageFormModal.tsx"
copy_src "features/sandbox-containers/SandboxContainersPage.tsx"
copy_src "features/sandbox-containers/SandboxContainerFormModal.tsx"
copy_src "features/sandbox-containers/PortMappingEditor.tsx"
copy_src "features/work-projects/WorkProjectsPage.tsx"
copy_src "features/work-projects/WorkProjectFormModal.tsx"
copy_src "features/work-projects/WorkProjectWorkspacePage.tsx"
copy_src "features/work-projects/WorkProjectInfoModal.tsx"
copy_src "features/work-projects/ProjectRecordViews.tsx"
copy_src "features/work-projects/ProjectGraphCanvas.tsx"
copy_src "features/work-projects/workProjectView.tsx"
copy_src "features/system-config/SystemConfigPage.tsx"

# Playground
copy_src "features/playground/PlaygroundPage.tsx"
copy_src "features/playground/Composer.tsx"
copy_src "features/playground/SessionList.tsx"
copy_src "features/playground/ChatStream.tsx"
copy_src "features/playground/SandboxSelector.tsx"
copy_src "features/playground/PlaygroundSandboxCreateModal.tsx"
copy_src "features/playground/AgentPicker.tsx"
copy_src "features/playground/SubagentSidePanel.tsx"
copy_src "features/playground/ImagePreview.tsx"
copy_src "features/playground/MessageScrollPanel.tsx"
copy_src "features/playground/subagentView.ts"
copy_src "features/playground/Transcript.tsx"
copy_src "features/playground/TranscriptExecutions.tsx"

# Container shell
copy_src "features/container-shell/ContainerFileManager.tsx"
copy_src "features/container-shell/FileViewer.tsx"
copy_src "features/container-shell/ContainerShellProvider.tsx"

# Landing
copy_src "features/landing/LandingContent.tsx"
copy_src "features/landing/landingConfig.ts"
copy_src "features/landing/LandingPage.tsx"

# HTML files
if [ -f "$PERSIST_DIR/web-html/app-index.html" ]; then
    cp "$PERSIST_DIR/web-html/app-index.html" "$PROJECT_DIR/web/app/index.html"
fi
if [ -f "$PERSIST_DIR/web-html/landing-index.html" ]; then
    cp "$PERSIST_DIR/web-html/landing-index.html" "$PROJECT_DIR/web/landing/index.html"
fi

# CSS theme files (white/light theme)
copy_src "app/styles/base.css"
copy_src "app/styles/login.css"
copy_src "app/styles/landing.css"
copy_src "app/styles/admin.css"

# Landing page SEO + Vite config (brand names in meta/title)
if [ -f "$SRC_BASE/landing.seo.ts" ]; then
    cp "$SRC_BASE/landing.seo.ts" "$PROJECT_DIR/web/landing.seo.ts"
fi
if [ -f "$SRC_BASE/vite.landing.config.ts" ]; then
    cp "$SRC_BASE/vite.landing.config.ts" "$PROJECT_DIR/web/vite.landing.config.ts"
fi

# Logo replacement (keep z3r0-logo.png filename to preserve import paths)
if [ -f "$PERSIST_DIR/assets/daybreak-logo.png" ]; then
    cp "$PERSIST_DIR/assets/daybreak-logo.png" "$PROJECT_DIR/web/src/assets/z3r0-logo.png"
fi

echo "  ✓ 中文翻译源文件已复制"

# 3. Setup Python virtual environment
echo "[3/8] 检查 Python 虚拟环境..."
if [ ! -d "$PROJECT_DIR/.venv" ]; then
    echo "  创建虚拟环境..."
    cd "$PROJECT_DIR"
    python3 -m venv .venv
    .venv/bin/pip install --upgrade pip
    .venv/bin/pip install -r "$PERSIST_DIR/requirements.txt"
    echo "  ✓ 虚拟环境创建完成"
else
    echo "  ✓ 虚拟环境已存在"
fi

# 4. Configure Docker TCP API (port 2375)
echo "[4/8] 检查 Docker 配置..."
DOCKER_DAEMON="/etc/docker/daemon.json"
if [ -f "$DOCKER_DAEMON" ]; then
    if ! grep -q "2375" "$DOCKER_DAEMON" 2>/dev/null; then
        echo "  ⚠ Docker daemon.json 未配置 TCP API (port 2375)"
        echo "  请手动添加: {\"hosts\": [\"tcp://0.0.0.0:2375\", \"npipe://.\"]}"
    else
        echo "  ✓ Docker TCP API 已配置"
    fi
else
    echo "  ⚠ Docker daemon.json 不存在"
    echo "  正在创建..."
    mkdir -p /etc/docker
    cp "$PERSIST_DIR/docker-daemon.json" "$DOCKER_DAEMON"
    echo "  ✓ Docker daemon.json 已创建 (需要重启 Docker 生效)"
fi

# 5. Check PostgreSQL container
echo "[5/8] 检查 PostgreSQL..."
PG_RUNNING=$(docker ps --filter "name=daybreak-postgres" --format "{{.Names}}" 2>/dev/null || true)
if [ -z "$PG_RUNNING" ]; then
    echo "  启动 PostgreSQL 容器..."
    docker start daybreak-postgres 2>/dev/null || \
    docker run -d --name daybreak-postgres \
        -e POSTGRES_USER=root \
        -e POSTGRES_PASSWORD=123456 \
        -e POSTGRES_DB=daybreak \
        -p 5432:5432 \
        postgres:16-alpine
    sleep 2
    echo "  ✓ PostgreSQL 已启动"
else
    echo "  ✓ PostgreSQL 已运行"
fi

# 6. Fix admin password hash (safe to run every time)
echo "[6/8] 修复管理员密码..."
cd "$PROJECT_DIR"
if [ -f "$PERSIST_DIR/init-db.py" ]; then
    .venv/bin/python "$PERSIST_DIR/init-db.py" 2>/dev/null && echo "  ✓ 管理员密码已更新" || echo "  ⚠ 密码更新跳过 (数据库可能未就绪)"
else
    echo "  ⚠ init-db.py 不存在, 跳过密码修复"
fi

# 6b. Install report generation endpoint
echo "[6b/8] 安装报告生成端点..."
mkdir -p "$PROJECT_DIR/service/work_project"
mkdir -p "$PROJECT_DIR/handler/work_project"
cp "$PERSIST_DIR/services/report_service.py" "$PROJECT_DIR/service/work_project/report.py"
cp "$PERSIST_DIR/handlers/work_project/report.py" "$PROJECT_DIR/handler/work_project/report.py"
# Patch router: add report route import + route definition
.venv/bin/python "$PERSIST_DIR/patch_report_route.py"
mkdir -p "$PROJECT_DIR/reports"
echo "  ✓ 报告生成端点已安装"

# 7. Kill existing Daybreak process and start fresh
echo "[7/8] 启动 破晓 Daybreak 服务..."
EXISTING_PID=$(pgrep -f "python.*main.py" 2>/dev/null || true)
if [ -n "$EXISTING_PID" ]; then
    echo "  终止旧进程 (PID: $EXISTING_PID)..."
    kill $EXISTING_PID 2>/dev/null
    sleep 1
fi

cd "$PROJECT_DIR"
setsid .venv/bin/python main.py > /tmp/daybreak.log 2>&1 &
sleep 2

# Check if process started
NEW_PID=$(pgrep -f "python.*main.py" 2>/dev/null || true)
if [ -n "$NEW_PID" ]; then
    echo ""
    echo "=========================================="
    echo "  ✓ 破晓 Daybreak 启动成功!"
    echo "  PID: $NEW_PID"
    echo "  地址: http://127.0.0.1:8000"
    echo "  账号: admin@daybreak.local"
    echo "  密码: admin"
    echo "  日志: /tmp/daybreak.log"
    echo "=========================================="
else
    echo ""
    echo "  ✗ 启动失败, 请查看日志: /tmp/daybreak.log"
    tail -20 /tmp/daybreak.log
fi
