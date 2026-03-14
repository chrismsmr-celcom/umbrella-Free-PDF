from PIL import Image, ImageEnhance
import os

def handle_scan_effect(image_path, output_dir):
    """Transforme une image en PDF avec un effet 'document scanné'"""
    img = Image.open(image_path).convert("L") # Noir et blanc
    
    # Amélioration du contraste pour faire ressortir le texte
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(2.0) 
    
    pdf_path = os.path.join(output_dir, "scanned_document.pdf")
    img.save(pdf_path, "PDF", resolution=100.0)
    return pdf_path