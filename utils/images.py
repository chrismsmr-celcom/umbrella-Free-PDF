import os
import fitz  # pip install pymupdf
from PIL import Image

def images_to_pdf(image_paths, output_path):
    """
    Convertit une liste d'images (JPG, PNG) en un seul fichier PDF.
    Utile pour la fonction 'Images en PDF' d'Umbrella.
    """
    try:
        img_list = []
        for path in image_paths:
            img = Image.open(path)
            # Conversion en RGB obligatoire pour le format PDF (élimine la couche Alpha des PNG)
            if img.mode != "RGB":
                img = img.convert("RGB")
            img_list.append(img)
        
        if img_list:
            # Sauvegarde du premier avec tous les suivants en pages additionnelles
            img_list[0].save(
                output_path, 
                "PDF", 
                save_all=True, 
                append_images=img_list[1:]
            )
            return output_path
    except Exception as e:
        print(f"❌ Erreur images_to_pdf : {e}")
        return None
    return None

def pdf_to_images(pdf_path, output_dir, fmt="jpg"):
    """
    Convertit chaque page d'un PDF en image individuelle.
    Idéal pour l'aperçu ou le partage de documents.
    """
    try:
        # Ouverture du document
        doc = fitz.open(pdf_path)
        saved_paths = []
        
        for i in range(len(doc)):
            page = doc.load_page(i)
            
            # Matrix(2, 2) augmente la résolution pour éviter le flou (équivalent ~150-200 DPI)
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            
            image_name = f"page_{i+1}.{fmt}"
            image_path = os.path.join(output_dir, image_name)
            
            # Sauvegarde de l'image
            pix.save(image_path)
            saved_paths.append(image_path)
            
        doc.close()
        return saved_paths
    except Exception as e:
        print(f"❌ Erreur pdf_to_images : {e}")
        return []