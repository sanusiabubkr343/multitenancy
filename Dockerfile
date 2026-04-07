# Dockerfile.dev
FROM python:3.11

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install watchfiles for hot-reload
RUN pip install watchfiles

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run with hot-reload for development
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]