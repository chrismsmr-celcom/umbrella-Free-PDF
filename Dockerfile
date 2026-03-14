# Utiliser une image Python légère mais complète
FROM python:3.10-slim

# Optimisations Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Installer les dépendances système
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-writer \
    libreoffice-calc \
    libreoffice-impress \
    fonts-liberation \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-fra \
    tesseract-ocr-eng \
    ghostscript \
    python3-tk \
    libgl1 \
    default-jre \
    libpango-1.0-0 \
    libharfbuzz0b \
    libpangoft2-1.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Cache des dépendances (Toujours copier le requirements seul avant pour gagner du temps au build)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le projet
COPY . .

# Sécurité : Création d'utilisateur et de dossiers temporaires
RUN useradd -m umbrella_user && \
    mkdir -p /tmp/libreoffice_profile /app/assets && \
    chown -R umbrella_user:umbrella_user /tmp/libreoffice_profile /app

USER umbrella_user

# EXPOSE est pour la documentation, Render gère le reste
EXPOSE 10000

# Commande de lancement avec un seul worker pour économiser la RAM sur le plan gratuit
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000} --workers 1"]
