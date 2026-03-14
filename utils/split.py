from pypdf import PdfReader, PdfWriter
import os

def handle_split(input_path, output_dir):
    """Sépare chaque page du PDF en un fichier individuel"""
    reader = PdfReader(input_path)
    split_files = []
    
    for i, page in enumerate(reader.pages):
        writer = PdfWriter()
        writer.add_page(page)
        
        filename = f"split_page_{i+1}.pdf"
        out_path = os.path.join(output_dir, filename)
        
        with open(out_path, "wb") as f:
            writer.write(f)
        split_files.append(out_path)
        
    return split_files