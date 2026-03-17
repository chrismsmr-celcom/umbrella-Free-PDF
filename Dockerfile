# Utiliser l'image Python slim comme base
FROM python:3.10-slim

# Optimisations Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Configuration LibreOffice & Temp (Correction pour permissions)
ENV HOME=/home/umbrella_user
ENV UserInstallation=file:///tmp/libreoffice

# 1. Configurer les dépôts pour inclure 'contrib' et 'non-free' (Polices MS)
# 2. Accepter la licence Microsoft automatiquement
# 3. Installer les dépendances système critiques
RUN sed -i 's/main/main contrib non-free/g' /etc/apt/sources.list.d/debian.sources || \
    sed -i 's/main/main contrib non-free/g' /etc/apt/sources.list && \
    echo "ttf-mscorefonts-installer msttcorefonts/accepted-mscorefonts-eula select true" | debconf-set-selections && \
    apt-get update && apt-get install -y --no-install-recommends \
    # Office & Java (Nécessaire pour certaines conversions)
    libreoffice-writer libreoffice-calc libreoffice-impress default-jre fonts-liberation \
    # PDF, OCR & Ghostscript
    poppler-utils tesseract-ocr tesseract-ocr-fra tesseract-ocr-eng ghostscript \
    # Dépendances graphiques (INDISPENSABLE pour OpenCV et Signature)
    libgl1 libglib2.0-0 libgdk-pixbuf2.0-0 \
    # Dépendances pour WEASYPRINT (HTML-to-PDF)
    libpango-1.0-0 libharfbuzz0b libpangoft2-1.0-0 libffi-dev libxml2-dev libxslt1-dev \
    # Polices Windows (Fidélité maximale pour conversion Office)
    ttf-mscorefonts-installer \
    # Utilitaires
    python3-tk curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Créer l'utilisateur non-root pour la sécurité
RUN useradd -m umbrella_user

WORKDIR /app

# Installer les dépendances Python (Utilisation du cache Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copier le reste du projet
COPY . .

# Gérer les dossiers temporaires et les droits d'accès
RUN mkdir -p /app/assets /tmp/umbrella_scans /tmp/libreoffice && \
    chown -R umbrella_user:umbrella_user /app /tmp/umbrella_scans /tmp/libreoffice

# Passer en utilisateur non-root
USER umbrella_user

# Render utilise dynamiquement le port via la variable PORT
EXPOSE 10000

# Lancement avec un timeout élevé (important pour l'OCR et LibreOffice)
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000} --workers 1 --timeout-keep-alive 600"]
