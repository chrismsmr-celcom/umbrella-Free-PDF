import os
import requests
from io import BytesIO
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from PIL import Image

# URL de ton logo
LOGO_URL = "https://oysdycuouodarfkmdtop.supabase.co/storage/v1/object/public/LOGO/Moniteo.png"

# Cache pour éviter de surcharger le réseau (ISO 9001: Efficacité des ressources)
CACHED_LOGO_DATA = None

def get_logo():
    global CACHED_LOGO_DATA
    if CACHED_LOGO_DATA is None:
        try:
            response = requests.get(LOGO_URL, timeout=5)
            if response.status_code == 200:
                CACHED_LOGO_DATA = response.content
        except Exception as e:
            print(f"⚠️ Erreur récupération logo : {e}")
    return CACHED_LOGO_DATA

def create_watermark():
    packet = BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)
    
    logo_data = get_logo()
    
    # Configuration de la transparence (ISO : Qualité visuelle non obstructive)
    # 0.15 = 15% d'opacité, très discret mais présent
    transparency = 0.15 
    
    if logo_data:
        try:
            img_buffer = BytesIO(logo_data)
            logo_img = ImageReader(img_buffer)
            
            # Application de la transparence
            can.setFillAlpha(transparency)
            
            # Positionnement discret en bas à droite
            # Largeur réduite à 60 pour plus de finesse
            can.drawImage(logo_img, 480, 20, width=60, preserveAspectRatio=True, mask='auto')
            
        except Exception as e:
            # Fallback ultra-discret si l'image crash
            can.setFillAlpha(0.2)
            can.setFont("Helvetica", 7)
            can.drawRightString(580, 20, "Powered by Moniteo (v.ISO)")
    else:
        can.setFillAlpha(0.2)
        can.setFont("Helvetica", 7)
        can.drawRightString(580, 20, "Powered by Moniteo")

    can.save()
    packet.seek(0)
    return packet

def apply_watermark(input_pdf_path):
    """Applique le logo selon les standards de qualité ISO 9001"""
    try:
        if not os.path.exists(input_pdf_path):
            return input_pdf_path

        watermark_packet = create_watermark()
        watermark_pdf = PdfReader(watermark_packet)
        watermark_page = watermark_pdf.pages[0]

        reader = PdfReader(input_pdf_path)
        writer = PdfWriter()

        for page in reader.pages:
            # Fusion du filigrane
            page.merge_page(watermark_page)
            writer.add_page(page)

        # Écriture sécurisée pour garantir l'intégrité du document
        temp_out = BytesIO()
        writer.write(temp_out)
        temp_out.seek(0)

        with open(input_pdf_path, "wb") as output_file:
            output_file.write(temp_out.read())
            
        return input_pdf_path
    except Exception as e:
        # En cas d'erreur, on livre le document brut (Continuité de service ISO)
        print(f"❌ Erreur Watermark : {e}")
        return input_pdf_path
