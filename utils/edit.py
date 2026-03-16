import os
from PIL import Image
from pdf2image import convert_from_path

def process_edit(input_path, output_path, rotation=0, crop_data=None):
    is_pdf = input_path.lower().endswith('.pdf')
    
    if is_pdf:
        # Convertir le PDF en image
        images = convert_from_path(input_path, first_page=1, last_page=1)
        if not images:
            raise ValueError("Impossible de convertir le PDF en image")
        img = images[0]
    else:
        # Ouvrir l'image normalement
        img = Image.open(input_path)

    # 1. Rotation (Pillow tourne en sens inverse de Cropper.js, donc -rotation)
    if rotation != 0:
        img = img.rotate(-rotation, expand=True)

    # 2. Recadrage
    if crop_data:
        width, height = img.size
        # Calcul des coordonnées en pixels à partir des pourcentages
        left = (crop_data['x'] * width) / 100
        top = (crop_data['y'] * height) / 100
        right = left + (crop_data['w'] * width) / 100
        bottom = top + (crop_data['h'] * height) / 100
        
        # Sécurité : s'assurer que les valeurs ne dépassent pas les limites
        img = img.crop((max(0, left), max(0, top), min(width, right), min(height, bottom)))

    # Sauvegarde
    img.convert('RGB').save(output_path, "PDF", resolution=100.0)
    return output_path
