# 1. Use official Python lightweight image
FROM python:3.10-slim

# 2. Prevent Python from writing .pyc files & buffer output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. Install System Dependencies for OCR, PDF processing, and Database
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 4. Set the working directory inside the container
WORKDIR /app

# 5. Copy requirements file
COPY requirements.txt .

# 6. ULTIMATE FIX: Install everything in one go, but FORCE pip to use the CPU server for PyTorch
RUN pip install --no-cache-dir -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu

# 7. Copy the rest of your backend project files
COPY . .

# 8. Expose the port
EXPOSE 10000

# 9. Start the FastAPI server using Uvicorn
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "10000"]