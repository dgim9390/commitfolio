# CommitFolio 배포 이미지: 화면(React 빌드)과 API(FastAPI)를 컨테이너 하나로.
# Render, Railway 등 Docker를 지원하는 곳이면 그대로 올릴 수 있다.

# ---- 1단계: 화면 빌드 (결과물 frontend/dist만 다음 단계로 가져간다)
FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- 2단계: 실행 환경
FROM python:3.12-slim
# 커밋 diff를 읽으려고 레포를 git clone 하므로 git이 필요하다
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv==0.13.0

# root가 아닌 사용자로 실행한다 (컨테이너가 뚫려도 피해를 줄이기 위해)
RUN useradd -m -u 1000 app && mkdir /app && chown app /app
USER app
WORKDIR /app
ENV UV_PYTHON_DOWNLOADS=never UV_LINK_MODE=copy

# 의존성 먼저 설치 → 코드만 바뀌면 이 층은 캐시를 재사용해 빌드가 빨라진다
COPY --chown=app backend/pyproject.toml backend/uv.lock backend/
RUN cd backend && uv sync --frozen --no-dev --no-install-project
COPY --chown=app backend/ backend/
RUN cd backend && uv sync --frozen --no-dev
COPY --chown=app --from=web /web/dist frontend/dist

# 캐시·결과 저장 위치. 디스크가 유지되는 볼륨이 있으면 CACHE_DIR로 그 경로를 지정한다
ENV CACHE_DIR=/app/.cache PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "cd backend && exec .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
