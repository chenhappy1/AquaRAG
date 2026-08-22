# Stage 1: Build dependencies
FROM python:3.11-slim AS base
WORKDIR /app

# Install system dependencies required by PyPDF2, docx, BeautifulSoup, etc.
RUN apt-get update && apt-get install -y \
    build-essential \
    libxml2 \
    libxslt1.1 \
    libjpeg62-turbo \
    libpng16-16 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Run FastAPI with Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]