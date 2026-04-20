import os
import shutil
import tempfile
import zipfile
from io import BytesIO

def cleanup(temp_dir: str):
    """
    Supprime le dossier temporaire après la réponse.
    Indispensable pour la survie du serveur en production sur Render.
    """
    if not temp_dir or not os.path.exists(temp_dir):
        return

    try:
        # ignore_errors=True est crucial car LibreOffice ou Tesseract 
        # peuvent mettre quelques millisecondes de trop à relâcher un fichier.
        shutil.rmtree(temp_dir, ignore_errors=True)
        print(f"🧹 Nettoyage réussi : {temp_dir}")
    except Exception as e:
        print(f"⚠️ Erreur lors du nettoyage de {temp_dir} : {e}")

def get_temp_dir():
    """Crée un dossier temporaire sécurisé avec le préfixe Umbrella"""
    return tempfile.mkdtemp(prefix="umbrella_")

def create_zip_from_files(file_paths: list):
    """
    Prend une liste de chemins et retourne un flux BytesIO (ZIP en mémoire).
    Rapide, mais attention à la RAM si les fichiers sont énormes (>100Mo).
    """
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file_path in file_paths:
            if file_path and os.path.exists(file_path):
                zip_file.write(file_path, arcname=os.path.basename(file_path))
    
    zip_buffer.seek(0)
    return zip_buffer

def create_zip_on_disk(file_paths, output_zip_path):
    """
    Crée un fichier ZIP directement sur le disque.
    Beaucoup plus sûr pour Render car cela n'utilise pas la RAM du serveur.
    C'est cette fonction que ton main.py utilise actuellement.
    """
    try:
        with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in file_paths:
                if os.path.exists(file):
                    zipf.write(file, os.path.basename(file))
        return output_zip_path
    except Exception as e:
        print(f"❌ Erreur lors de la création du ZIP sur disque : {e}")
        return None
