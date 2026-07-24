# ── 破晓 Daybreak 安全评估平台 ── 多阶段构建 ──────────────────────────────────

# ── Stage 1: 构建前端 (从源码) ────────────────────────────────────────────────
FROM node:22-alpine AS web-builder

WORKDIR /app/web

# 先装依赖 (利用 Docker 缓存)
COPY web/package*.json ./
RUN npm ci

# 复制前端源码
COPY web/ ./

# ── 注入破晓定制文件 ──
# CSS 白色主题
COPY daybreak-persist/web-src/app/styles/base.css     src/app/styles/base.css
COPY daybreak-persist/web-src/app/styles/login.css     src/app/styles/login.css
COPY daybreak-persist/web-src/app/styles/landing.css   src/app/styles/landing.css
COPY daybreak-persist/web-src/app/styles/admin.css     src/app/styles/admin.css

# 品牌 Logo (保持 z3r0-logo.png 文件名)
COPY daybreak-persist/assets/daybreak-logo.png         src/assets/z3r0-logo.png

# HTML 标题
COPY daybreak-persist/web-html/app-index.html          app/index.html

# 共享翻译
COPY daybreak-persist/web-src/shared/lib/uiText.ts     src/shared/lib/uiText.ts
COPY daybreak-persist/web-src/shared/lib/labels.ts     src/shared/lib/labels.ts
COPY daybreak-persist/web-src/shared/lib/date.ts       src/shared/lib/date.ts
COPY daybreak-persist/web-src/shared/components/ResourcePageShell.tsx  src/shared/components/ResourcePageShell.tsx
COPY daybreak-persist/web-src/shared/components/ResourceCells.tsx      src/shared/components/ResourceCells.tsx
COPY daybreak-persist/web-src/shared/api/feedback.ts                   src/shared/api/feedback.ts
COPY daybreak-persist/web-src/main.tsx                src/main.tsx

# 布局 & 登录
COPY daybreak-persist/web-src/app/layouts/AdminLayout.tsx  src/app/layouts/AdminLayout.tsx
COPY daybreak-persist/web-src/features/auth/LoginPage.tsx  src/features/auth/LoginPage.tsx

# 系统管理页面
COPY daybreak-persist/web-src/features/system-users/       src/features/system-users/
COPY daybreak-persist/web-src/features/hosts/              src/features/hosts/
COPY daybreak-persist/web-src/features/egress-proxies/     src/features/egress-proxies/
COPY daybreak-persist/web-src/features/sandbox-images/     src/features/sandbox-images/
COPY daybreak-persist/web-src/features/sandbox-containers/ src/features/sandbox-containers/
COPY daybreak-persist/web-src/features/work-projects/      src/features/work-projects/
COPY daybreak-persist/web-src/features/system-config/      src/features/system-config/

# Playground
COPY daybreak-persist/web-src/features/playground/         src/features/playground/

# 容器 Shell
COPY daybreak-persist/web-src/features/container-shell/    src/features/container-shell/

# Landing
COPY daybreak-persist/web-src/features/landing/LandingContent.tsx  src/features/landing/LandingContent.tsx
COPY daybreak-persist/web-src/features/landing/landingConfig.ts    src/features/landing/landingConfig.ts
COPY daybreak-persist/web-src/features/landing/LandingPage.tsx     src/features/landing/LandingPage.tsx

# Landing SEO
COPY daybreak-persist/web-src/landing.seo.ts              landing.seo.ts
COPY daybreak-persist/web-src/vite.landing.config.ts       vite.landing.config.ts

# 构建 SPA
RUN npx vite build --config vite.app.config.ts

# ── Stage 2: 后端 ──────────────────────────────────────────────────────────────
FROM python:3.13-slim AS backend

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Python 依赖 (利用缓存)
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir python-docx==1.1.2

# 后端源码
COPY app.py config.py database.py logger.py main.py ./
COPY core        ./core
COPY middleware   ./middleware
COPY model        ./model
COPY schema       ./schema
COPY utils        ./utils
COPY scripts      ./scripts
COPY sandbox      ./sandbox
COPY docs         ./docs

# Router (先复制原始)
COPY router       ./router

# Service / Handler (复制原始 + 覆盖定制)
COPY service      ./service
COPY handler      ./handler

# 覆盖: 报告生成服务
COPY daybreak-persist/services/report_service.py   ./service/work_project/report.py
COPY daybreak-persist/handlers/work_project/report.py ./handler/work_project/report.py

# 前端构建产物
COPY --from=web-builder /app/web/dist-app ./web/dist-app

# 注入报告路由补丁 (在构建时完成 patch)
COPY daybreak-persist/patch_report_route.py /tmp/patch_report_route.py
RUN python /tmp/patch_report_route.py && rm /tmp/patch_report_route.py

# 创建 reports 目录和 .daybreak 工作区
RUN mkdir -p /app/reports /app/.daybreak

# 复制默认配置和智能体提示词
COPY deploy/config.default.json /app/.daybreak/config.json
COPY daybreak-persist/agents/ /app/.daybreak/agents/

EXPOSE 8000

CMD ["python", "main.py"]
