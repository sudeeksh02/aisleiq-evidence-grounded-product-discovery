FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml README.md ./
COPY aisleiq ./aisleiq
COPY scripts ./scripts
RUN pip install --no-cache-dir '.[semantic,ranker]'
COPY . .
RUN mkdir -p data/processed data/raw
EXPOSE 8000
CMD ["uvicorn", "aisleiq.api:app", "--host", "0.0.0.0", "--port", "8000"]
