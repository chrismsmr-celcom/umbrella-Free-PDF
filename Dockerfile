# Utiliser l'image Python slim comme base
FROM python:3.10-slim-bookworm

# Optimisations Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Configuration
ENV HOME=/home/umbrella_user
ENV TMPDIR=/tmp/umbrella

# Installation des dépendances système (minimales)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    ca-certificates \
    # OCR
    tesseract-ocr \
    tesseract-ocr-fra \
    tesseract-ocr-eng \
    # LibreOffice
    libreoffice-writer \
    libreoffice-calc \
    libreoffice-impress \
    # Utilitaires
    poppler-utils \
    ghostscript \
    libgl1 \
    libglib2.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Installation de ocrmypdf via pip (plus fiable)
RUN pip install --no-cache-dir ocrmypdf

# Copie des requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Création de l'utilisateur
RUN useradd -m -u 1000 umbrella_user && \
    mkdir -p /app /tmp/umbrella /tmp/umbrella_scans && \
    chown -R umbrella_user:umbrella_user /app /tmp/umbrella /tmp/umbrella_scans

WORKDIR /app
COPY --chown=umbrella_user:umbrella_user . .

USER umbrella_user
EXPOSE 10000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000} --workers 1 --limit-concurrency 10 --timeout-keep-alive 120"]