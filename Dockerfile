# Utiliser l'image Python slim comme base
FROM python:3.10-slim-bookworm

# Optimisations Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Configuration
ENV HOME=/home/umbrella_user
ENV TMPDIR=/tmp/umbrella

<<<<<<< HEAD
# Installation des dépendances système (minimales)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    ca-certificates \
    # OCR
=======
# Installation des dépendances système (version corrigée)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    gnupg \
    wget \
    # OCR et traitement d'images
    ocrmypdf \
>>>>>>> 03c6a701209ed4de9936dfeff38bba4b863774da
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
<<<<<<< HEAD
=======
    libgdk-pixbuf2.0-0 \
    libpango-1.0-0 \
    libharfbuzz0b \
    libpangoft2-1.0-0 \
    libffi-dev \
    libxml2-dev \
    libxslt1-dev \
>>>>>>> 03c6a701209ed4de9936dfeff38bba4b863774da
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

<<<<<<< HEAD
# Installation de ocrmypdf via pip (plus fiable)
RUN pip install --no-cache-dir ocrmypdf

# Copie des requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Création de l'utilisateur
=======
# Installation des polices Microsoft (séparée pour éviter les erreurs)
RUN apt-get update && \
    echo "ttf-mscorefonts-installer msttcorefonts/accepted-mscorefonts-eula select true" | debconf-set-selections && \
    apt-get install -y --no-install-recommends ttf-mscorefonts-installer || true && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Création de l'utilisateur non-root
>>>>>>> 03c6a701209ed4de9936dfeff38bba4b863774da
RUN useradd -m -u 1000 umbrella_user && \
    mkdir -p /app /tmp/umbrella /tmp/umbrella_scans && \
    chown -R umbrella_user:umbrella_user /app /tmp/umbrella /tmp/umbrella_scans

WORKDIR /app
COPY --chown=umbrella_user:umbrella_user . .

USER umbrella_user
EXPOSE 10000

<<<<<<< HEAD
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000} --workers 1 --limit-concurrency 10 --timeout-keep-alive 120"]
=======
# Script de démarrage optimisé
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000} --workers 1 --limit-concurrency 10 --timeout-keep-alive 120 --no-access-log --log-level warning"]
>>>>>>> 03c6a701209ed4de9936dfeff38bba4b863774da
