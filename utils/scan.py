from PIL import Image, ImageEnhance
import os
import gc

def handle_scan_effect(image_path, output_dir, mode="color"):
    """Transforme une image en PDF avec effet scan optimisé pour Render"""
    try:
        img = Image.open(image_path)
        
        # 1. RÉDUCTION DE LA RÉSOLUTION (Sécurité RAM Render)
        # Un scan n'a pas besoin de 4000px. 2000px est largement suffisant pour du PDF.
        max_size = 2000
        if max(img.size) > max_size:
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        
        # 2. GESTION DES MODES
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        if mode == "grayscale":
            # Transformation N&B optimisée
            img = img.convert("L")
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(2.0) 
            # On reconvertit en RGB pour la compatibilité PDF standard
            img = img.convert("RGB")
        else:
            # Boost léger des couleurs et contraste pour l'effet "propre"
            enhancer = ImageEnhance.Color(img)
            img = enhancer.enhance(1.2)
            enhancer_contrast = ImageEnhance.Contrast(img)
            img = enhancer_contrast.enhance(1.1)

        # 3. GÉNÉRATION DU CHEMIN
        # On simplifie le nom pour éviter les doubles extensions bizarres
        safe_name = os.path.basename(image_path).split('.')[0]
        pdf_filename = f"scan_{safe_name}.pdf"
        pdf_path = os.path.join(output_dir, pdf_filename)
        
        # 4. SAUVEGARDE OPTIMISÉE
        # resolution=72 ou 100 est parfait pour le web
        img.save(pdf_path, "PDF", resolution=100.0, optimize=True)
        
        # 5. NETTOYAGE STRICT
        img.close()
        gc.collect()
        
        return pdf_path

    except Exception as e:
        print(f"❌ Erreur Scan: {e}")
        # En cas d'erreur, on essaie de libérer la RAM quand même
        if 'img' in locals(): img.close()
        gc.collect()
        return None
