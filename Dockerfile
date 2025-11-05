# Use an official lightweight Python image
FROM python:3.11-slim

# Copy dependencies
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy the entire app
COPY . .

# Expose the app port (change if needed)
EXPOSE 5000

# Start the app
CMD ["python", "app.py"]
