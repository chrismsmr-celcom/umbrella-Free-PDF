from pypdf import PdfReader, PdfWriter
import os
import io

def handle_reorder(input_path, pages_str, temp_dir):
    """Réorganise les pages selon l'ordre donné (ex: '3,1,2')"""
    reader = PdfReader(input_path)
    writer = PdfWriter()
    new_order = [int(p.strip()) - 1 for p in pages_str.split(",") if p.strip()]
    
    for idx in new_order:
        if 0 <= idx < len(reader.pages):
            writer.add_page(reader.pages[idx])
            
    output_path = os.path.join(temp_dir, "umbrella_reordered.pdf")
    with open(output_path, "wb") as f:
        writer.write(f)
    return output_path

def handle_extract(input_path, pages_str, temp_dir):
    """Extrait uniquement les pages sélectionnées"""
    reader = PdfReader(input_path)
    writer = PdfWriter()
    indices = [int(p.strip()) - 1 for p in pages_str.split(",") if p.strip()]
    
    for idx in indices:
        if 0 <= idx < len(reader.pages):
            writer.add_page(reader.pages[idx])
            
    output_path = os.path.join(temp_dir, "umbrella_extracted.pdf")
    with open(output_path, "wb") as f:
        writer.write(f)
    return output_path

def handle_remove(input_path, pages_str, temp_dir):
    """Supprime les pages sélectionnées"""
    reader = PdfReader(input_path)
    writer = PdfWriter()
    to_remove = [int(p.strip()) - 1 for p in pages_str.split(",") if p.strip()]
    
    for i in range(len(reader.pages)):
        if i not in to_remove:
            writer.add_page(reader.pages[i])
            
    output_path = os.path.join(temp_dir, "umbrella_removed.pdf")
    with open(output_path, "wb") as f:
        writer.write(f)
    return output_path

def handle_merge(files_paths, temp_dir):
    """Fusionne plusieurs fichiers PDF en un seul"""
    writer = PdfWriter()
    for path in files_paths:
        reader = PdfReader(path)
        for page in reader.pages:
            writer.add_page(page)
            
    output_path = os.path.join(temp_dir, "umbrella_merged.pdf")
    with open(output_path, "wb") as f:
        writer.write(f)
    return output_path