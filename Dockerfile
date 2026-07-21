# syntax=docker/dockerfile:1

ARG NUCLEI_VERSION=3.8.0
ARG NUCLEI_RELEASE_BASE_URL=https://github.com/projectdiscovery/nuclei/releases/download

FROM python:3.13-slim AS nuclei-builder
ARG NUCLEI_VERSION
ARG NUCLEI_RELEASE_BASE_URL
ARG TARGETARCH
RUN set -eux; \
    case "${TARGETARCH:-amd64}" in amd64) nuclei_arch=amd64 ;; arm64) nuclei_arch=arm64 ;; *) exit 1 ;; esac; \
    export NUCLEI_VERSION NUCLEI_RELEASE_BASE_URL nuclei_arch; \
    python -c 'import os, urllib.request, zipfile; version=os.environ["NUCLEI_VERSION"]; base=os.environ["NUCLEI_RELEASE_BASE_URL"]; arch=os.environ["nuclei_arch"]; urllib.request.urlretrieve(f"{base}/v{version}/nuclei_{version}_linux_{arch}.zip", "/tmp/nuclei.zip"); zipfile.ZipFile("/tmp/nuclei.zip").extract("nuclei", "/usr/local/bin")'; \
    chmod 755 /usr/local/bin/nuclei; \
    /usr/local/bin/nuclei -version

FROM node:22-alpine AS web-builder

WORKDIR /app/web

COPY web/package*.json ./
RUN npm ci

COPY web/ ./
RUN npm run build


FROM python:3.13-slim AS backend

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt

COPY app.py config.py database.py logger.py main.py ./
COPY core ./core
COPY handler ./handler
COPY middleware ./middleware
COPY model ./model
COPY router ./router
COPY schema ./schema
COPY service ./service
COPY utils ./utils
COPY --from=nuclei-builder /usr/local/bin/nuclei /usr/local/bin/nuclei
COPY --from=web-builder /app/web/dist-app ./web/dist-app

EXPOSE 8000

CMD ["python", "main.py"]
