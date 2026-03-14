import io
import base64
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

def process_pdf_signature(file_bytes, signature_base64, x=100, y=100):
    try:
        # 1. Décoder l'image
        header, encoded = signature_base64.split(",", 1)
        sig_data = base64.b64decode(encoded)
        
        # On utilise ImageReader pour transformer les bytes en objet lisible par ReportLab
        sig_img = ImageReader(io.BytesIO(sig_data))

        # 2. Créer le calque de signature
        packet = io.BytesIO()
        can = canvas.Canvas(packet)
        
        # Dessiner l'image
        # ReportLab accepte l'objet ImageReader
        can.drawImage(sig_img, x, y, width=150, height=75, mask='auto')
        can.save()
        packet.seek(0)
        
        overlay_pdf = PdfReader(packet)
        overlay_page = overlay_pdf.pages[0]

        # 3. Charger le PDF original
        # On s'assure de passer un BytesIO à PdfReader
        original_pdf = PdfReader(io.BytesIO(file_bytes))
        writer = PdfWriter()

        # 4. Fusion sur la dernière page
        for i, page in enumerate(original_pdf.pages):
            if i == len(original_pdf.pages) - 1:
                page.merge_page(overlay_page)
            writer.add_page(page)

        output = io.BytesIO()
        writer.write(output)
        output.seek(0)
        
        return output
    except Exception as e:
        # On remonte l'erreur réelle pour le débuggage
        raise Exception(f"Erreur interne sign_utils: {str(e)}")