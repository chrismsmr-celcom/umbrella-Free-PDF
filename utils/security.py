import os
from pypdf import PdfReader, PdfWriter  # <--- CORRECTION ICI (pypdf en minuscules)

def protect_pdf(input_path, output_dir, password):
    try:
        reader = PdfReader(input_path)
        writer = PdfWriter()

        for page in reader.pages:
            writer.add_page(page)

        # Application du mot de passe
        writer.encrypt(password)

        output_path = os.path.join(output_dir, f"protected_{os.path.basename(input_path)}")
        with open(output_path, "wb") as f:
            writer.write(f)
            
        return output_path
    except Exception as e:
        print(f"Erreur protection PDF: {e}")
        return None
def unlock_pdf(input_path, output_dir, password):
    try:
        reader = PdfReader(input_path)
        writer = PdfWriter()

        # On vérifie si le PDF est bien chiffré
        if reader.is_encrypted:
            # Tentative de déchiffrement
            status = reader.decrypt(password)
            if status == 0:  # 0 signifie échec (souvent lié au type de chiffrement ou mauvais pass)
                # Note: status peut aussi être un objet de permissions selon la version
                pass 
        
        # On copie les pages (si le decrypt a réussi, elles seront lisibles)
        for page in reader.pages:
            writer.add_page(page)

        output_path = os.path.join(output_dir, f"unlocked_{os.path.basename(input_path)}")
        with open(output_path, "wb") as f:
            writer.write(f)
            
        return output_path
    except Exception as e:
        print(f"Erreur déverrouillage PDF: {e}")
        return None
