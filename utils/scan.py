from PIL import Image, ImageEnhance
import os
import gc

def handle_scan_effect(image_path, output_dir, mode="color"):
    """Transforme une image en PDF avec effet scan (couleur ou N&B)"""
    try:
        img = Image.open(image_path)
        
        # Sécurité : Convertir en RGB pour éviter l'erreur d'enregistrement PDF
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        if mode == "grayscale":
            img = img.convert("L")
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(2.0) 
            # On repasse en RGB car save(PDF) n'aime pas toujours le mode L pur
            img = img.convert("RGB")
        else:
            enhancer = ImageEnhance.Color(img)
            img = enhancer.enhance(1.2)
            enhancer_contrast = ImageEnhance.Contrast(img)
            img = enhancer_contrast.enhance(1.1)

        pdf_filename = f"scan_{os.path.basename(image_path)}.pdf"
        pdf_path = os.path.join(output_dir, pdf_filename)
        
        # Sauvegarde avec optimisation
        img.save(pdf_path, "PDF", resolution=100.0)
        
        # Libération immédiate de la mémoire
        img.close()
        gc.collect()
        
        return pdf_path
    except Exception as e:
        print(f"❌ Erreur Scan: {e}")
        return None
