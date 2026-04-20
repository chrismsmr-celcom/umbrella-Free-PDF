from pypdf import PdfWriter
import os, uuid

def handle_merge(files_paths, output_dir):
    merger = PdfWriter()
    for path in files_paths:
        if os.path.exists(path):
            merger.append(path)
    
    # Utilisation d'un ID court pour le nom de fichier
    short_id = uuid.uuid4().hex[:8]
    output_path = os.path.join(output_dir, f"merged_{short_id}.pdf")
    
    with open(output_path, "wb") as f:
        merger.write(f)
    
    merger.close()
    return output_path