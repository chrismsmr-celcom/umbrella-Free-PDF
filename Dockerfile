# Utiliser l'image Python slim comme base
FROM python:3.10-slim-bookworm

# Optimisations Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Configuration LibreOffice & Temp (Correction pour permissions)
ENV HOME=/home/umbrella_user
ENV UserInstallation=file:///tmp/libreoffice

# 1. Utilisation de composants logiciels pour activer contrib et non-free proprement
# 2. Acceptation de la licence MS
# 3. Installation des dépendances
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl gnupg && \
    # Étape 1 : On force la configuration des dépôts (contrib et non-free)
    # On crée un nouveau fichier source propre au lieu de modifier l'existant
    echo "deb http://deb.debian.org/debian bookworm main contrib non-free" > /etc/apt/sources.list.d/umbrella.list && \
    echo "deb http://deb.debian.org/debian bookworm-updates main contrib non-free" >> /etc/apt/sources.list.d/umbrella.list && \
    echo "deb http://security.debian.org/debian-security bookworm-security main contrib non-free" >> /etc/apt/sources.list.d/umbrella.list && \
    # Étape 2 : On supprime les anciens fichiers qui pourraient créer des conflits
    rm -f /etc/apt/sources.list.d/debian.sources && \
    # Étape 3 : On accepte la licence MS et on installe tout
    echo "ttf-mscorefonts-installer msttcorefonts/accepted-mscorefonts-eula select true" | debconf-set-selections && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    libreoffice-writer libreoffice-calc libreoffice-impress default-jre fonts-liberation \
    poppler-utils tesseract-ocr tesseract-ocr-fra tesseract-ocr-eng ghostscript \
    libgl1 libglib2.0-0 libgdk-pixbuf2.0-0 \
    libgl1 libglib2.0-0 libgdk-pixbuf2.0-0 \
    libpango-1.0-0 libharfbuzz0b libpangoft2-1.0-0 libffi-dev libxml2-dev libxslt1-dev \
    ttf-mscorefonts-installer curl \
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
