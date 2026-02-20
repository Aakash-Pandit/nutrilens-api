# --- Stage 1: Build Stage ---
FROM python:3.11-slim as builder

# Set environment variables to optimize Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies needed for building Python packages (like gcc)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies into a virtual env or local folder
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt


# --- Stage 2: Runtime Stage ---
FROM python:3.11-slim

WORKDIR /app

# 1. Install RUNTIME system dependencies (Tesseract + OpenCV helpers)
# Note: We use 'libgl1' and 'libglx-mesa0' for OpenCV support
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    libgl1 \
    libglx-mesa0 \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# 2. Copy installed Python packages from the builder stage
COPY --from=builder /install /usr/local

# 3. Copy your Django project code
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port Django runs on
EXPOSE 8000

# Run the application (using Gunicorn for production)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
