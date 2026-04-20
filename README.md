# 🛡️ Umbrella PDF Engine PRO

Moteur performant de manipulation de documents PDF et Office basé sur FastAPI et Docker. Conçu pour être déployé sur Render ou en local.

## 🚀 Fonctionnalités
- **Organize** : Merge, Split, Remove, Extract, Reorder.
- **Convert** : Office vers PDF (LibreOffice), PDF vers Word/Excel/PPTX.
- **Édition** : Signature numérique, Compression, Réparation, PDF/A.
- **Images** : Images vers PDF, PDF vers JPG/PNG.
- **Security** : Protection par mot de passe et déverrouillage.
- **OCR** : Reconnaissance optique de caractères via Tesseract (Fr/En).
- **Scan** : Simulation de numérisation via mobile (QR Code).

## 🛠️ Installation & Lancement

### Avec Docker (Recommandé)
```bash
# Construction de l'image
docker build -t umbrella-engine .

# Lancement du conteneur (Port 10000 pour Render)
docker run -p 10000:10000 umbrella-engine
