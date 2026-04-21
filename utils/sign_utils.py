import os
import base64
import io
from PIL import Image, ImageDraw, ImageFont
from typing import Optional, Tuple
from pypdf import PdfReader, PdfWriter

def process_pdf_signature(
    file_bytes: bytes, 
    signature_base64: str, 
    position: str = "bottom-left",
    all_pages: bool = False
) -> io.BytesIO:
    """
    Ajoute une signature à un PDF avec choix de l'emplacement
    """
    try:
        # Vérifier que c'est bien un PDF
        if not file_bytes.startswith(b'%PDF'):
            raise ValueError("Le fichier fourni n'est pas un PDF valide")
        
        if "," in signature_base64:
            signature_base64 = signature_base64.split(",")[1]
        
        signature_bytes = base64.b64decode(signature_base64)
        signature_img = Image.open(io.BytesIO(signature_bytes))
        
        # Redimensionner
        max_width = 200
        max_height = 80
        if signature_img.width > max_width or signature_img.height > max_height:
            ratio = min(max_width / signature_img.width, max_height / signature_img.height)
            new_size = (int(signature_img.width * ratio), int(signature_img.height * ratio))
            signature_img = signature_img.resize(new_size, Image.Resampling.LANCZOS)
        
        # Convertir en RGB
        if signature_img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', signature_img.size, (255, 255, 255))
            if signature_img.mode == 'RGBA':
                background.paste(signature_img, mask=signature_img.split()[3])
            else:
                background.paste(signature_img)
            signature_img = background
        
        temp_signature = io.BytesIO()
        signature_img.save(temp_signature, 'PNG')
        temp_signature.seek(0)
        
        reader = PdfReader(io.BytesIO(file_bytes))
        writer = PdfWriter()
        
        # Vérifier que le PDF a des pages
        if len(reader.pages) == 0:
            raise ValueError("Le PDF est vide")
        
        # Déterminer les pages à signer
        pages_to_sign = range(len(reader.pages)) if all_pages else [len(reader.pages) - 1]
        
        for i, page in enumerate(reader.pages):
            writer.add_page(page)
            
            if i in pages_to_sign:
                # Calculer les coordonnées
                page_width = float(page.mediabox.width)
                page_height = float(page.mediabox.height)
                img_width = signature_img.width
                img_height = signature_img.height
                
                margin = 50
                
                if position == 'top-left':
                    x, y = margin, margin
                elif position == 'top-right':
                    x, y = page_width - img_width - margin, margin
                elif position == 'top-center':
                    x, y = (page_width - img_width) / 2, margin
                elif position == 'middle-left':
                    x, y = margin, (page_height - img_height) / 2
                elif position == 'center':
                    x, y = (page_width - img_width) / 2, (page_height - img_height) / 2
                elif position == 'middle-right':
                    x, y = page_width - img_width - margin, (page_height - img_height) / 2
                elif position == 'bottom-left':
                    x, y = margin, page_height - img_height - margin
                elif position == 'bottom-center':
                    x, y = (page_width - img_width) / 2, page_height - img_height - margin
                else:
                    x, y = page_width - img_width - margin, page_height - img_height - margin
                
                signature_page = PdfReader(temp_signature).pages[0]
                page.merge_page(signature_page, over=True, transform=(1, 0, 0, 1, x, y))
        
        output = io.BytesIO()
        writer.write(output)
        output.seek(0)
        
        return output
        
    except Exception as e:
        print(f"Erreur signature: {e}")
        raise

def create_text_signature(name: str, initials: str, color: str = "#555555") -> str:
    """
    Crée une signature textuelle
    """
    try:
        img_width = 300
        img_height = 100
        
        img = Image.new('RGB', (img_width, img_height), 'white')
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
        except:
            font = ImageFont.load_default()
        
        draw.text((20, 30), name, fill=color, font=font)
        
        from datetime import datetime
        date_str = datetime.now().strftime("%d/%m/%Y")
        try:
            small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        except:
            small_font = ImageFont.load_default()
        draw.text((20, 70), f"Signe le: {date_str}", fill="#888888", font=small_font)
        
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        return f"data:image/png;base64,{img_base64}"
        
    except Exception as e:
        print(f"Erreur creation signature texte: {e}")
        return None

def create_stamp_signature(company_name: str, company_info: str, color: str = "#555555") -> str:
    """
    Crée un tampon d'entreprise
    """
    try:
        img_width = 400
        img_height = 150
        
        img = Image.new('RGB', (img_width, img_height), 'white')
        draw = ImageDraw.Draw(img)
        
        try:
            font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
            font_normal = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        except:
            font_title = ImageFont.load_default()
            font_normal = ImageFont.load_default()
        
        draw.rectangle([10, 10, img_width - 10, img_height - 10], outline=color, width=2)
        draw.text((20, 30), company_name, fill=color, font=font_title)
        draw.text((20, 65), company_info, fill="#888888", font=font_normal)
        
        from datetime import datetime
        date_str = datetime.now().strftime("%d/%m/%Y")
        draw.text((20, 100), f"Date: {date_str}", fill="#888888", font=font_normal)
        
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        return f"data:image/png;base64,{img_base64}"
        
    except Exception as e:
        print(f"Erreur creation tampon: {e}")
        return None
