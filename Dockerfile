# Utiliser l'image Python slim comme base
FROM python:3.10-slim

# Optimisations Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Configuration LibreOffice & Temp
ENV HOME=/home/umbrella_user
ENV OFFICE_PROFILE=/tmp/libreoffice

# 1. Configurer les dépôts pour inclure 'contrib' et 'non-free'
# 2. Accepter la licence Microsoft automatiquement
# 3. Installer les dépendances
RUN sed -i 's/main/main contrib non-free/g' /etc/apt/sources.list.d/debian.sources || \
    sed -i 's/main/main contrib non-free/g' /etc/apt/sources.list && \
    echo "ttf-mscorefonts-installer msttcorefonts/accepted-mscorefonts-eula select true" | debconf-set-selections && \
    apt-get update && apt-get install -y --no-install-recommends \
    # Office & Java
    libreoffice-writer libreoffice-calc libreoffice-impress default-jre fonts-liberation \
    # PDF, OCR & Ghostscript
    poppler-utils tesseract-ocr tesseract-ocr-fra tesseract-ocr-eng ghostscript \
    # Dépendances graphiques
    python3-tk libgl1 libpango-1.0-0 libharfbuzz0b libpangoft2-1.0-0 \
    # Polices Windows (Fidélité maximale)
    ttf-mscorefonts-installer \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Créer l'utilisateur non-root
RUN useradd -m umbrella_user

WORKDIR /app

# Installer les dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copier le projet
COPY . .

# Gérer les droits
RUN mkdir -p /app/assets /tmp/umbrella_scans /tmp/libreoffice && \
    chown -R umbrella_user:umbrella_user /app /tmp/umbrella_scans /tmp/libreoffice

USER umbrella_user

EXPOSE 10000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000} --workers 1 --timeout-keep-alive 600"]
