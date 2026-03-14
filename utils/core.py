import os
import shutil
import tempfile
import zipfile
from io import BytesIO

def cleanup(temp_dir: str):
    """
    Supprime le dossier temporaire après la réponse.
    Indispensable pour la survie du serveur en production.
    """
    try:
        if os.path.exists(temp_dir):
            # ignore_errors=True évite les blocages si un processus 
            # (comme LibreOffice) n'a pas tout à fait relâché le dossier
            shutil.rmtree(temp_dir, ignore_errors=True)
            print(f"🧹 Nettoyage réussi : {temp_dir}")
    except Exception as e:
        print(f"⚠️ Erreur lors du nettoyage : {e}")

def get_temp_dir():
    """Crée un dossier temporaire sécurisé"""
    return tempfile.mkdtemp()

def create_zip_from_files(file_paths: list):
    """
    Prend une liste de chemins de fichiers et retourne un flux BytesIO (ZIP).
    Utilisé par main.py pour le traitement par lots (Batch Processing).
    """
    zip_buffer = BytesIO()
    
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file_path in file_paths:
            if file_path and os.path.exists(file_path):
                # On ajoute le fichier dans le ZIP en gardant son nom d'origine
                # arcname évite de recréer toute l'arborescence des dossiers dans le ZIP
                zip_file.write(file_path, arcname=os.path.basename(file_path))
    
    # Très important : on remet le curseur au début du flux avant l'envoi
    zip_buffer.seek(0)
    return zip_buffer
    import zipfile
import os

def create_zip_on_disk(file_paths, output_zip_path):
    """Crée un fichier ZIP sur le disque à partir d'une liste de chemins."""
    with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in file_paths:
            if os.path.exists(file):
                zipf.write(file, os.path.basename(file))