# Utiliser l'image Python slim comme base
FROM python:3.10-slim

# Optimisations Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Configuration LibreOffice & Temp
ENV HOME=/home/umbrella_user
ENV OFFICE_PROFILE=/tmp/libreoffice

# Installer TOUTES les dépendances système en une seule fois
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Office & Java
    libreoffice-writer libreoffice-calc libreoffice-impress default-jre fonts-liberation \
    # PDF, OCR & Ghostscript (Crucial pour Camelot/PDF-A)
    poppler-utils tesseract-ocr tesseract-ocr-fra tesseract-ocr-eng ghostscript \
    # Dépendances graphiques et polices pour la fidélité
    python3-tk libgl1 libpango-1.0-0 libharfbuzz0b libpangoft2-1.0-0 \
    # Optionnel mais recommandé pour la fidélité des polices Windows
    ttf-mscorefonts-installer \ 
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Créer l'utilisateur non-root
RUN useradd -m umbrella_user

WORKDIR /app

# 1. Installer les dépendances Python (Mise en cache efficace)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 2. Copier le reste du projet
COPY . .

# 3. Gérer les droits proprement
RUN mkdir -p /app/assets /tmp/umbrella_scans /tmp/libreoffice && \
    chown -R umbrella_user:umbrella_user /app /tmp/umbrella_scans /tmp/libreoffice

USER umbrella_user

# Port pour Render
EXPOSE 10000

# Commande de lancement (1 worker pour la RAM de Render)
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000} --workers 1 --timeout-keep-alive 600"]
