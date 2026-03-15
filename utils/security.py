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
