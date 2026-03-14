import zipfile
from io import BytesIO

def create_zip_from_files(file_paths):
    """Prend une liste de chemins de fichiers et retourne un objet BytesIO contenant le ZIP"""
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file_path in file_paths:
            if file_path and os.path.exists(file_path):
                # On ajoute le fichier en gardant uniquement son nom (pas le chemin complet)
                zip_file.write(file_path, os.path.basename(file_path))
    
    zip_buffer.seek(0)
    return zip_buffer