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

# 6. Install PyTorch CPU version explicitly FIRST
RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# 7. ULTIMATE FIX: Remove any mention of 'torch' from the copied requirements.txt inside Docker 
# so pip doesn't try to "upgrade" or overwrite our perfect CPU installation.
RUN grep -v "torch" requirements.txt > temp.txt && mv temp.txt requirements.txt

# 8. Install the rest of the packages normally
RUN pip install --no-cache-dir -r requirements.txt

# 9. Copy the rest of your backend project files
COPY . .

# 10. Expose the port
EXPOSE 10000

# 11. Start the FastAPI server using Uvicorn
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "10000"]