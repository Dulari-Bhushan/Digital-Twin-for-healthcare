# Stage 1: build the React dashboard
FROM node:20-alpine AS web
WORKDIR /web
COPY dashboard/package.json dashboard/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY dashboard/ ./
RUN npm run build

# Stage 2: API + built dashboard + precomputed demo artifacts (no GPU needed)
FROM python:3.11-slim
WORKDIR /app
COPY requirements-api.txt ./
RUN pip install --no-cache-dir -r requirements-api.txt
COPY src/ ./src/
COPY artifacts/ ./artifacts/
COPY --from=web /web/dist ./dashboard/dist
ENV KAYA_ARTIFACTS=/app/artifacts/demo
EXPOSE 8000
# Hosts such as Render choose the port and pass it as PORT; locally it stays 8000.
CMD ["sh", "-c", "uvicorn app:app --app-dir src/api --host 0.0.0.0 --port ${PORT:-8000}"]
