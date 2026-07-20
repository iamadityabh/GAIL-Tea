# 1. Use official Python lightweight image
FROM python:3.10-slim

# 2. Prevent Python from writing .pyc files & buffer output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 🔥 ADDED: DOCKER-SPECIFIC OLLAMA URL
ENV OLLAMA_BASE_URL="http://host.docker.internal:11434"

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

# 6. Install EVERYTHING (Forcing CPU version where possible)
RUN pip install --no-cache-dir -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu

# 7. Uninstall the problematic audio and vision libraries
# sentence-transformers only needs 'torch'. Removing torchaudio completely prevents the C++ crash.
RUN pip uninstall -y torchvision torchaudio

# 8. 🔥 ADDED: PRE-DOWNLOAD THE EMBEDDING MODEL FOR OFFLINE USE
# Isko COPY . . se pehle rakha hai taaki code change hone par baar-baar model download na ho!
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-mpnet-base-v2')"

# 9. Copy the rest of your backend project files
COPY . .

# 10. Expose the port
EXPOSE 10000

# 11. Start the FastAPI server using Uvicorn
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "10000"]