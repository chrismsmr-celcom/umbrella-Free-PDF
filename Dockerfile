# Utiliser une image Python légère mais complète
FROM python:3.10-slim

# Optimisations Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Définit le dossier Home de LibreOffice pour éviter les erreurs de droits
ENV HOME=/tmp

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
    # AJOUT : wkhtmltopdf pour ta route html-to-pdf
    wkhtmltopdf \
    # AJOUT : xfonts pour le rendu des textes HTML
    xfonts-75dpi \
    xfonts-base \
    python3-tk \
    libgl1 \
    default-jre \
    libpango-1.0-0 \
    libharfbuzz0b \
    libpangoft2-1.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Cache des dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le projet
COPY . .

# Sécurité : Création d'utilisateur et de dossiers temporaires
# On donne les droits sur /tmp car LibreOffice y écrit son profil utilisateur
RUN useradd -m umbrella_user && \
    mkdir -p /app/assets && \
    chown -R umbrella_user:umbrella_user /app /tmp

USER umbrella_user

# Render injecte automatiquement la variable PORT
EXPOSE 10000

# Commande de lancement
# Le --timeout-keep-alive 600 est utile pour les gros fichiers PDF
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000} --workers 1 --timeout-keep-alive 600"]
