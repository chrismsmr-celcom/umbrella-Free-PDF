import os
from PIL import Image
from pdf2image import convert_from_path

def process_edit(input_path, output_path, rotation=0, crop_data=None):
    """
    Gère la rotation et le recadrage. 
    crop_data = {"x":, "y":, "w":, "h":} (pourcentages 0-100)
    """
    # Si c'est un PDF, on convertit la page 1 en image pour l'éditer
    is_pdf = input_path.lower().endswith('.pdf')
    if is_pdf:
        images = convert_from_path(input_path, first_page=1, last_page=1)
        img = images[0]
    else:
        img = Image.open(input_path)

    # 1. Rotation
    if rotation != 0:
        img = img.rotate(-rotation, expand=True) # - car Pillow tourne CCW

    # 2. Recadrage (si fourni)
    if crop_data:
        width, height = img.size
        left = (crop_data['x'] * width) / 100
        top = (crop_data['y'] * height) / 100
        right = left + (crop_data['w'] * width) / 100
        bottom = top + (crop_data['h'] * height) / 100
        img = img.crop((left, top, right, bottom))

    # Sauvegarde finale en PDF
    img.convert('RGB').save(output_path, "PDF", resolution=100.0)
    return output_path
