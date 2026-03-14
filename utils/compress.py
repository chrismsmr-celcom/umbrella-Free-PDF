import os
from pypdf import PdfReader, PdfWriter

def handle_compress(input_path, output_dir, quality="medium"):
    try:
        reader = PdfReader(input_path)
        writer = PdfWriter()

        # 1. On définit la force de réduction selon ton "Umbrella Style"
        # On va jouer sur le sous-échantillonnage des images (image_quality)
        if quality == "extreme":
            img_quality = 30  # Qualité basse, fichier très léger
        elif quality == "medium":
            img_quality = 60  # Compromis idéal
        else:
            img_quality = 85  # Qualité haute

        for page in reader.pages:
            writer.add_page(page)

        # 2. La clé est ici : on itère sur les pages du writer pour réduire les images
        for page in writer.pages:
            # On compresse le contenu textuel (ton code d'origine)
            page.compress_content_streams() 
            
            # On réduit la taille des images (c'est ça qui fait gagner des Mo !)
            # Cette méthode va re-compresser les images présentes sur la page
            for img in page.images:
                img.replace(img.image, quality=img_quality)

        output_path = os.path.join(output_dir, f"compressed_{os.path.basename(input_path)}")
        
        with open(output_path, "wb") as f:
            writer.write(f)
            
        return output_path
    except Exception as e:
        print(f"DEBUG COMPRESS ERROR: {str(e)}")
        return None