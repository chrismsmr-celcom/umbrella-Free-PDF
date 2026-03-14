# Utiliser une image Python légère mais complète
FROM python:3.10-slim

# Optimisations Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Force le port pour Hugging Face
ENV PORT=7860

# Installer les dépendances système (Version Debian Trixie)
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

# Créer un utilisateur non-root (Hugging Face l'exige souvent implicitement via l'ID 1000)
RUN useradd -m -u 1000 umbrella_user
WORKDIR /app

# Copier et installer les dépendances
COPY --chown=umbrella_user:umbrella_user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le reste du projet
COPY --chown=umbrella_user:umbrella_user . .

# Créer les répertoires nécessaires avec les bonnes permissions
RUN mkdir -p /tmp/libreoffice_profile /app/assets && \
    chown -R umbrella_user:umbrella_user /tmp/libreoffice_profile /app

USER umbrella_user

# Port spécifique à Hugging Face
EXPOSE 7860

# Commande de lancement (0.0.0.0 est obligatoire)
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port 7860"]
