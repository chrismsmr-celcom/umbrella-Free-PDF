from pypdf import PdfReader, PdfWriter
import os

def handle_repair(input_path, output_dir):
    """Tente de réparer la structure d'un PDF corrompu"""
    try:
        reader = PdfReader(input_path)
        writer = PdfWriter()
        
        # On tente de copier chaque page dans un nouveau writer
        # Cela reconstruit la table XREF (souvent la cause des erreurs)
        for page in reader.pages:
            writer.add_page(page)
            
        out_path = os.path.join(output_dir, "repaired_document.pdf")
        with open(out_path, "wb") as f:
            writer.write(f)
        return out_path
    except Exception as e:
        # Si pypdf échoue, on peut renvoyer None pour signaler une erreur fatale
        print(f"Erreur de réparation : {e}")
        return None