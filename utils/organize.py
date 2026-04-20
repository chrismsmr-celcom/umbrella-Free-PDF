from pypdf import PdfReader, PdfWriter
import os

def handle_extract(input_path, pages_str, temp_dir):
    reader = PdfReader(input_path)
    writer = PdfWriter()
    
    # Conversion "1,2,5" -> [0, 1, 4]
    indices = [int(p.strip()) - 1 for p in pages_str.split(",") if p.strip()]
    
    for idx in indices:
        if 0 <= idx < len(reader.pages):
            writer.add_page(reader.pages[idx])
            
    output_path = os.path.join(temp_dir, "umbrella_extracted.pdf")
    with open(output_path, "wb") as f:
        writer.write(f)
    return output_path

def handle_remove(input_path, pages_str, temp_dir):
    reader = PdfReader(input_path)
    writer = PdfWriter()
    
    # Pages à exclure
    to_remove = [int(p.strip()) - 1 for p in pages_str.split(",") if p.strip()]
    
    for i in range(len(reader.pages)):
        if i not in to_remove:
            writer.add_page(reader.pages[i])
            
    output_path = os.path.join(temp_dir, "umbrella_removed.pdf")
    with open(output_path, "wb") as f:
        writer.write(f)
    return output_path

def handle_reorder(input_path, pages_str, temp_dir):
    reader = PdfReader(input_path)
    writer = PdfWriter()
    
    # L'ordre exact envoyé par le Drag & Drop
    new_order = [int(p.strip()) - 1 for p in pages_str.split(",") if p.strip()]
    
    for idx in new_order:
        if 0 <= idx < len(reader.pages):
            writer.add_page(reader.pages[idx])
        
    output_path = os.path.join(temp_dir, "umbrella_reordered.pdf")
    with open(output_path, "wb") as f:
        writer.write(f)
    return output_path