# Utiliser l'image Python slim comme base
FROM python:3.10-slim-bookworm AS builder

# Optimisations Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Installation des dépendances de build
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copie des requirements pour l'installation
COPY requirements.txt .

# Installation des dépendances Python (cache Docker)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Étape finale (plus petite)
FROM python:3.10-slim-bookworm

# Optimisations Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Configuration LibreOffice & Temp
ENV HOME=/home/umbrella_user
ENV TMPDIR=/tmp/umbrella
ENV NUMBA_CACHE_DIR=/tmp/numba_cache

# Installation des dépendances système
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    gnupg \
    wget \
    # OCR et traitement d'images
    tesseract-ocr \
    tesseract-ocr-fra \
    tesseract-ocr-eng \
    ghostscript \
    poppler-utils \
    # LibreOffice (conversion Office)
    libreoffice-writer \
    libreoffice-calc \
    libreoffice-impress \
    default-jre-headless \
    fonts-liberation \
    fonts-dejavu \
    # Dépendances système
    libgl1 \
    libglib2.0-0 \
    libgdk-pixbuf2.0-0 \
    libpango-1.0-0 \
    libharfbuzz0b \
    libpangoft2-1.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Installation de ocrmypdf via pip (plus fiable)
RUN pip install --no-cache-dir ocrmypdf

# Création de l'utilisateur non-root
RUN useradd -m -u 1000 umbrella_user && \
    mkdir -p /app /tmp/umbrella /tmp/umbrella_scans /tmp/libreoffice /tmp/numba_cache && \
    chown -R umbrella_user:umbrella_user /app /tmp/umbrella /tmp/umbrella_scans /tmp/libreoffice /tmp/numba_cache

WORKDIR /app

# Copie des dépendances Python depuis builder
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copie du code source
COPY --chown=umbrella_user:umbrella_user . .

# Configuration des permissions
RUN chmod -R 755 /app && \
    chmod 755 /tmp/umbrella /tmp/umbrella_scans

# Variables d'environnement pour l'optimisation
ENV PYTHONPATH=/app
ENV OMP_NUM_THREADS=1
ENV MKL_NUM_THREADS=1
ENV OPENBLAS_NUM_THREADS=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-10000}/ || exit 1

# Passage à l'utilisateur non-root
USER umbrella_user

# Exposition du port
EXPOSE 10000

# Script de démarrage optimisé
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000} --workers 1 --limit-concurrency 10 --timeout-keep-alive 120 --no-access-log --log-level warning"]
