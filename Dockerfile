# Utiliser l'image Python slim comme base
FROM python:3.10-slim

# Optimisations Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Configuration LibreOffice & Temp pour éviter les erreurs de permissions
ENV HOME=/home/umbrella_user
ENV OFFICE_PROFILE=/tmp/libreoffice

# Installer les dépendances système (Triées pour la clarté)
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Pour la conversion Office (Le plus lourd)
    libreoffice-writer libreoffice-calc libreoffice-impress default-jre fonts-liberation \
    # Pour PDF to Image et Scan
    poppler-utils tesseract-ocr tesseract-ocr-fra tesseract-ocr-eng \
    # Pour OpenCV, WeasyPrint et Ghostscript
    ghostscript python3-tk libgl1 libpango-1.0-0 libharfbuzz0b libpangoft2-1.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Créer l'utilisateur non-root tôt
RUN useradd -m umbrella_user

WORKDIR /app

# 1. Installer les dépendances Python (Cache)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 2. Copier le reste du projet
COPY . .

# 3. Gérer les droits proprement
# On crée les dossiers nécessaires et on donne les droits à l'utilisateur
RUN mkdir -p /app/assets /tmp/umbrella_scans /tmp/libreoffice && \
    chown -R umbrella_user:umbrella_user /app /tmp/umbrella_scans /tmp/libreoffice

USER umbrella_user

# Render utilise le port définit par la variable d'env PORT
EXPOSE 10000

# Commande de lancement robuste
# On limite les workers à 1 pour économiser la RAM sur Render
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000} --workers 1 --timeout-keep-alive 600"]
