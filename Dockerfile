# Multi-stage build for Flask Banking App
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies (only for compilation, not in final image)
RUN apt-get update && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies system-wide
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# ---- Final Stage ----
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies (if needed)
RUN apt-get update && apt-get install -y --no-install-recommends sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder (optional but keeps final image small)
COPY --from=builder /usr/local /usr/local

# Copy your app code
COPY . .

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    FLASK_APP=app.py

# Create non-root user for better security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose the Flask port
EXPOSE 5000

# Run Flask app using Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "3", "app:app"]
