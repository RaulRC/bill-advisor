FROM node:24-slim AS frontend
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY pyproject.toml ./
COPY bill_advisor/ bill_advisor/
COPY api/ api/
COPY --from=frontend /app/dist frontend/dist

RUN pip install --no-cache-dir .

EXPOSE 8000
EXPOSE 8001

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
