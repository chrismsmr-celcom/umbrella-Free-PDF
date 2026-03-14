import os
from PyPDF2 import PdfReader, PdfWriter

def protect_pdf(input_path, output_dir, password):
    try:
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        output_path = os.path.join(output_dir, f"{base_name}_protected.pdf")
        
        reader = PdfReader(input_path)
        writer = PdfWriter()

        # Copier toutes les pages
        for page in reader.pages:
            writer.add_page(page)

        # Appliquer le mot de passe
        writer.encrypt(password)

        with open(output_path, "wb") as f:
            writer.write(f)
            
        return output_path
    except Exception as e:
        print(f"❌ Erreur Protection PDF: {e}")
        return None