# Use an official lightweight Python image
FROM python:3.11-slim

# Copy dependencies
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy the entire app
COPY . .

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app && \
    chown -R appuser:appuser /root/.local

USER appuser

# Expose the app port 
EXPOSE 5000

# Start the app
CMD ["python", "app.py"]
