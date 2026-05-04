FROM python:3.12-slim

WORKDIR /app

# Build-time version injected into the API container
ARG APP_VERSION=dev
ENV APP_VERSION=$APP_VERSION

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy application code and install Python dependencies
COPY . .
RUN pip install --no-cache-dir -e .

# Run migrations on startup
ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
