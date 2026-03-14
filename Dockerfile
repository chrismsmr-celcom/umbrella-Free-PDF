# Utiliser une image Python légère mais complète
FROM python:3.10-slim

# Optimisations Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Installer les dépendances système (Version complète pour toutes les fonctions d'Umbrella)
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
    wkhtmltopdf \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Cache des dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le projet
COPY . .

# Sécurité : Utilisateur non-root
RUN useradd -m umbrella_user
RUN mkdir -p /tmp/libreoffice_profile && chown -R umbrella_user:umbrella_user /tmp/libreoffice_profile /app
USER umbrella_user

# EXPOSE est indicatif, Render utilise sa variable $PORT
EXPOSE 10000

# Commande de lancement dynamique optimisée pour Render
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000}"]
