from PIL import Image, ImageEnhance
import os

def handle_scan_effect(image_path, output_dir, mode="color"):
    """Transforme une image en PDF avec effet scan (couleur ou N&B)"""
    img = Image.open(image_path)
    
    if mode == "grayscale":
        img = img.convert("L")
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(2.0) # Boost contraste pour le texte
    else:
        # Optionnel: Améliorer légèrement les couleurs pour l'effet "scan"
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(1.2)
    
    pdf_path = os.path.join(output_dir, f"scan_{os.path.basename(image_path)}.pdf")
    img.save(pdf_path, "PDF", resolution=100.0)
    return pdf_path
