FROM python:3.11-slim
WORKDIR /app/backend
ENV PYTHONUNBUFFERED=1 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
RUN apt-get update && apt-get install -y --no-install-recommends git libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv==0.13.7
COPY pyproject.toml uv.lock README.md ./
COPY lunarcv ./lunarcv
COPY app ./app
COPY scripts ./scripts
RUN uv sync --frozen --no-dev
RUN mkdir -p /app/data/uploads /app/data/results /app/outputs/match_cache
EXPOSE 8000
CMD ["uv", "run", "--frozen", "--no-dev", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
