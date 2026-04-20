import os
import tempfile
from PIL import Image
from pdf2image import convert_from_path
import gc
from typing import Optional, Dict, Tuple

def process_edit(input_path: str, output_path: str, rotation: int = 0, crop_data: Optional[Dict] = None) -> Optional[str]:
    """
    Édite un PDF ou une image (rotation, recadrage) avec optimisation mémoire
    
    Args:
        input_path: Chemin du fichier source (PDF ou image)
        output_path: Chemin du fichier de sortie
        rotation: Angle de rotation en degrés
        crop_data: Dictionnaire avec x, y, w, h en pourcentages
    
    Returns:
        Chemin du fichier de sortie ou None en cas d'erreur
    """
    img = None
    images = None
    
    try:
        # Vérifier que le fichier existe
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Fichier introuvable: {input_path}")
        
        is_pdf = input_path.lower().endswith('.pdf')
        
        # --- 1. CHARGEMENT DE L'IMAGE ---
        if is_pdf:
            print(f"📄 Conversion PDF en image: {os.path.basename(input_path)}")
            
            # Optimisation pour PDF : première page seulement
            # Limiter la résolution pour économiser la RAM
            images = convert_from_path(
                input_path,
                first_page=1,
                last_page=1,
                dpi=150,  # DPI réduit pour économiser la RAM (150 au lieu de 200)
                size=(2000, None),  # Limiter la largeur max à 2000px
                fmt='jpeg',  # Format JPEG plus léger que PNG
                thread_count=1  # Un seul thread
            )
            
            if not images:
                raise ValueError("Impossible de convertir le PDF en image")
            
            img = images[0]
            # Libérer la mémoire de la liste
            images = None
            gc.collect()
            
        else:
            # Chargement d'image standard
            img = Image.open(input_path)
            
            # Optimisation : réduire si trop grande
            max_size = 2500
            if max(img.size) > max_size:
                ratio = max_size / max(img.size)
                new_size = tuple(int(dim * ratio) for dim in img.size)
                img.thumbnail(new_size, Image.Resampling.LANCZOS)
                print(f"📐 Image redimensionnée: {new_size[0]}x{new_size[1]}")
        
        # --- 2. CONVERSION EN RGB ---
        if img.mode in ('RGBA', 'LA', 'P'):
            # Créer un fond blanc pour les images transparentes
            if img.mode == 'RGBA':
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])
                img = background
            else:
                img = img.convert('RGB')
        
        # --- 3. ROTATION ---
        if rotation != 0:
            print(f"🔄 Rotation: {rotation}°")
            # Rotation avec expansion pour ne pas recadrer
            img = img.rotate(-rotation, expand=True, resample=Image.Resampling.BICUBIC)
        
        # --- 4. RECADRAGE ---
        if crop_data and all(k in crop_data for k in ['x', 'y', 'w', 'h']):
            print(f"✂️ Recadrage: x={crop_data['x']}%, y={crop_data['y']}%, w={crop_data['w']}%, h={crop_data['h']}%")
            
            width, height = img.size
            
            # Conversion pourcentages → pixels
            left = (crop_data['x'] * width) / 100
            top = (crop_data['y'] * height) / 100
            right = left + (crop_data['w'] * width) / 100
            bottom = top + (crop_data['h'] * height) / 100
            
            # Arrondir et sécuriser les valeurs
            left = max(0, int(round(left)))
            top = max(0, int(round(top)))
            right = min(width, int(round(right)))
            bottom = min(height, int(round(bottom)))
            
            # Vérifier que le recadrage est valide
            if right > left and bottom > top:
                img = img.crop((left, top, right, bottom))
            else:
                print(f"⚠️ Recadrage invalide, ignoré")
        
        # --- 5. NETTETÉ OPTIONNELLE (améliore le rendu après rotation/crop) ---
        if rotation != 0 or crop_data:
            from PIL import ImageFilter
            img = img.filter(ImageFilter.UnsharpMask(radius=0.5, percent=50, threshold=0))
        
        # --- 6. SAUVEGARDE OPTIMISÉE ---
        print(f"💾 Sauvegarde du PDF: {os.path.basename(output_path)}")
        
        # Utiliser une qualité adaptée
        img.save(
            output_path,
            "PDF",
            resolution=100.0,
            optimize=True,
            quality=85
        )
        
        # Vérifier que le fichier a bien été créé
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            file_size = os.path.getsize(output_path) // 1024
            print(f"✅ Édition terminée ({file_size}KB)")
            return output_path
        else:
            raise Exception("Fichier de sortie non généré")
        
    except MemoryError as e:
        print(f"❌ Erreur mémoire lors de l'édition: {e}")
        return None
        
    except Exception as e:
        print(f"❌ Erreur édition: {str(e)}")
        return None
        
    finally:
        # Nettoyage rigoureux
        if img:
            img.close()
        if images:
            for im in images:
                im.close()
        gc.collect()


def process_batch_edit(input_paths: list, output_dir: str, rotation: int = 0, crop_data: Optional[Dict] = None) -> list:
    """
    Traite plusieurs fichiers en batch (séquentiel pour économiser la RAM)
    
    Args:
        input_paths: Liste des chemins de fichiers
        output_dir: Dossier de sortie
        rotation: Angle de rotation
        crop_data: Données de recadrage
    
    Returns:
        Liste des fichiers de sortie générés
    """
    results = []
    
    for i, input_path in enumerate(input_paths):
        print(f"📄 Édition [{i+1}/{len(input_paths)}]: {os.path.basename(input_path)}")
        
        # Générer un nom de sortie unique
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        output_path = os.path.join(output_dir, f"edited_{base_name}_{i}.pdf")
        
        result = process_edit(input_path, output_path, rotation, crop_data)
        
        if result:
            results.append(result)
        
        # Forcer le garbage collector après chaque fichier
        gc.collect()
    
    return results


def get_image_info(input_path: str) -> Optional[Dict]:
    """
    Récupère les informations d'une image sans la charger entièrement
    
    Args:
        input_path: Chemin du fichier
    
    Returns:
        Dictionnaire avec les informations de l'image
    """
    try:
        with Image.open(input_path) as img:
            return {
                "width": img.width,
                "height": img.height,
                "mode": img.mode,
                "format": img.format,
                "is_pdf": input_path.lower().endswith('.pdf')
            }
    except Exception as e:
        print(f"❌ Erreur lecture infos: {e}")
        return None


def preview_edit(input_path: str, rotation: int = 0, crop_data: Optional[Dict] = None, preview_size: Tuple[int, int] = (800, 600)) -> Optional[Image.Image]:
    """
    Génère un aperçu des modifications sans sauvegarder (pour prévisualisation)
    
    Args:
        input_path: Chemin du fichier source
        rotation: Angle de rotation
        crop_data: Données de recadrage
        preview_size: Taille max de l'aperçu (largeur, hauteur)
    
    Returns:
        Image PIL pour prévisualisation ou None
    """
    img = None
    
    try:
        is_pdf = input_path.lower().endswith('.pdf')
        
        if is_pdf:
            # Pour l'aperçu, utiliser un DPI plus bas
            images = convert_from_path(
                input_path,
                first_page=1,
                last_page=1,
                dpi=72,  # DPI bas pour l'aperçu
                size=preview_size,
                fmt='jpeg',
                thread_count=1
            )
            if not images:
                return None
            img = images[0]
        else:
            img = Image.open(input_path)
        
        # Conversion RGB
        if img.mode in ('RGBA', 'LA', 'P'):
            if img.mode == 'RGBA':
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])
                img = background
            else:
                img = img.convert('RGB')
        
        # Rotation
        if rotation != 0:
            img = img.rotate(-rotation, expand=True, resample=Image.Resampling.BICUBIC)
        
        # Recadrage
        if crop_data and all(k in crop_data for k in ['x', 'y', 'w', 'h']):
            width, height = img.size
            left = (crop_data['x'] * width) / 100
            top = (crop_data['y'] * height) / 100
            right = left + (crop_data['w'] * width) / 100
            bottom = top + (crop_data['h'] * height) / 100
            
            left = max(0, int(round(left)))
            top = max(0, int(round(top)))
            right = min(width, int(round(right)))
            bottom = min(height, int(round(bottom)))
            
            if right > left and bottom > top:
                img = img.crop((left, top, right, bottom))
        
        # Redimensionner pour l'aperçu si nécessaire
        img.thumbnail(preview_size, Image.Resampling.LANCZOS)
        
        return img
        
    except Exception as e:
        print(f"❌ Erreur aperçu: {e}")
        return None
        
    finally:
        if img and not is_pdf:
            img.close()
        gc.collect()