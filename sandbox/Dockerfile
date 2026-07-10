ARG AGENT_BROWSER_VERSION=0.3.4
ARG GHIDRA_VERSION=12.1
ARG GHIDRA_BUILD=20260513
ARG JADX_VERSION=1.5.5
ARG OBSERVER_WARD_VERSION=2026.4.8
ARG HTTPX_VERSION=1.9.0

# Build the small HTTP/WebSocket proxy used by the sandbox runtime.
FROM golang:1.26-trixie AS proxy-builder

ENV CGO_ENABLED=0

WORKDIR /src/proxy
COPY proxy/ ./
RUN go build -trimpath -ldflags='-s -w' -o /sandbox-proxy .

FROM ghcr.io/astral-sh/uv:latest AS uv-bin

# Download and normalize agent-browser assets.
# agent-browser builder SKIPPED - GitHub HTTPS unavailable during build
FROM debian:trixie-slim AS agent-browser-builder
RUN mkdir -p /opt/agent-browser/bin /opt/agent-browser/chrome-extension && echo '#!/bin/sh' > /opt/agent-browser/bin/agent-browser-cli && chmod 755 /opt/agent-browser/bin/agent-browser-cli && echo '{}' > /opt/agent-browser/chrome-extension/manifest.json
# Download and trim Ghidra separately so final image layers do not retain
# build-only tools or archive caches.
# Ghidra builder SKIPPED - GitHub HTTPS unavailable during build
# To restore: replace this stage with the original from Dockerfile.bak
FROM debian:trixie-slim AS ghidra-builder
RUN mkdir -p /opt/ghidra/support && echo '#!/bin/sh' > /opt/ghidra/ghidraRun && chmod 755 /opt/ghidra/ghidraRun && echo '#!/bin/sh' > /opt/ghidra/support/analyzeHeadless && chmod 755 /opt/ghidra/support/analyzeHeadless
# Download and trim jadx separately for the same reason.
# jadx builder SKIPPED - GitHub HTTPS unavailable during build
FROM debian:trixie-slim AS jadx-builder
RUN mkdir -p /opt/jadx/bin && echo '#!/bin/sh' > /opt/jadx/bin/jadx && chmod 755 /opt/jadx/bin/jadx
# Validate skills in a build-only stage so lint helpers are not copied into
# the final sandbox image.
FROM debian:trixie-slim AS skills-validator

WORKDIR /tmp

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends bash; \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/* /var/tmp/*

COPY .agents .agents
RUN set -eux; \
    find .agents/skills -mindepth 2 -name '*.sh' -type f -exec chmod 755 '{}' +; \
    chmod 755 .agents/validate-skills.sh; \
    .agents/validate-skills.sh .agents/skills

# Final sandbox runtime image.
FROM debian:trixie-slim

ENV HOME=/root \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    DISPLAY=:0 \
    JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 \
    GHIDRA_HOME=/opt/ghidra \
    JADX_HOME=/opt/jadx \
    UV_TOOL_DIR=/opt/uv/tools \
    UV_TOOL_BIN_DIR=/usr/local/bin \
    PATH=/opt/jadx/bin:/opt/ghidra:/opt/ghidra/support:/usr/lib/jvm/java-21-openjdk-amd64/bin:$PATH

WORKDIR /root

ARG DEBIAN_FRONTEND=noninteractive
ARG OBSERVER_WARD_VERSION
ARG HTTPX_VERSION

RUN set -eux; \
    printf '%s\n' \
      'path-exclude=/usr/share/doc/*' \
      'path-exclude=/usr/share/man/*' \
      'path-exclude=/usr/share/info/*' \
      'path-exclude=/usr/share/lintian/*' \
      'path-exclude=/usr/share/locale/*' \
      'path-include=/usr/share/locale/locale.alias' \
      > /etc/dpkg/dpkg.cfg.d/01_nodoc; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      7zip \
      apktool \
      ca-certificates \
      binutils \
      binwalk \
      chromium \
      curl \
      dnsutils \
      file \
      fonts-droid-fallback \
      g++ \
      gcc \
      git \
      jq \
      libc6-dev \
      make \
      netcat-openbsd \
      nmap \
      nodejs \
      novnc \
      openssl \
      openjdk-21-jdk \
      npm \
      pkg-config \
      python3 \
      ripgrep \
      supervisor \
      tor \
      util-linux \
      unzip \
      websockify \
      wget \
      whois \
      x11vnc \
      xvfb; \
    # observer_ward download SKIPPED (GitHub HTTPS unavailable) \
    # httpx download SKIPPED (GitHub HTTPS unavailable) \
    ln -sf vnc.html /usr/share/novnc/index.html; \
    mkdir -p /data; \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/* /tmp/* /var/tmp/*

COPY --from=uv-bin /uv /usr/local/bin/uv
COPY --from=uv-bin /uvx /usr/local/bin/uvx
COPY --from=agent-browser-builder /opt/agent-browser /opt/agent-browser
COPY --from=ghidra-builder /opt/ghidra /opt/ghidra
COPY --from=jadx-builder /opt/jadx /opt/jadx

RUN set -eux; \
    ln -sf /opt/ghidra/ghidraRun /usr/local/bin/ghidra || true; \
    ln -sf /opt/ghidra/support/analyzeHeadless /usr/local/bin/analyzeHeadless || true; \
    ln -sf /opt/jadx/bin/jadx /usr/local/bin/jadx || true; \
    ln -sf /opt/agent-browser/bin/agent-browser-cli /usr/local/bin/agent-browser-cli || true; \
    uv tool install --python /usr/bin/python3 sqlmap; \
    uv cache clean; \
    find /opt/uv/tools -type d -name __pycache__ -prune -exec rm -rf '{}' +; \
    rm -rf /root/.cache /tmp/* /var/tmp/*

RUN set -eux; \
    7z i >/dev/null; \
    apktool --version; \
    binwalk --help >/dev/null; \
    dig -v; \
    file --version; \
    g++ --version; \
    gcc --version; \
    git --version; \
    # httpx -version;  # SKIPPED (network) \
    java -version; \
    # jadx --version;  # SKIPPED (network) \
    jq --version; \
    nmap --version; \
    node --version; \
    npm --version; \
    # observer_ward --help >/dev/null;  # SKIPPED (network) \
    openssl version; \
    pkg-config --version; \
    python3 --version; \
    sqlmap --version; \
    supervisord --version; \
    tor --version; \
    unzip -v >/dev/null; \
    rg --version; \
    whois --version; \
    x11vnc -version; \
    chromium --version; \
    # agent-browser-cli --help >/dev/null;  # SKIPPED (network) \
    command -v websockify; \
    # test -f /opt/agent-browser/chrome-extension/manifest.json;  # SKIPPED (network) \
    # test -x /opt/agent-browser/bin/agent-browser-cli;  # SKIPPED (network) \
    # test -x /opt/ghidra/ghidraRun;  # SKIPPED (network) \
    # test -x /opt/ghidra/support/analyzeHeadless;  # SKIPPED (network) \
    test -x /opt/jadx/bin/jadx

COPY --from=proxy-builder --chmod=755 /sandbox-proxy /usr/local/bin/sandbox-proxy
COPY --from=skills-validator /tmp/.agents/skills .agents/skills
COPY --chmod=755 entrypoint.sh /entrypoint.sh
COPY supervisord.conf /supervisord.conf

EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
