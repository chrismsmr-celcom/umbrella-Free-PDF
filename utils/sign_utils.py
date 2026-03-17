import io
import base64
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

def process_pdf_signature(file_bytes, signature_base64, x=50, y=50):
    try:
        # 1. Nettoyage et décodage du Base64
        if "," in signature_base64:
            header, encoded = signature_base64.split(",", 1)
        else:
            encoded = signature_base64
            
        sig_data = base64.b64decode(encoded)
        sig_img = ImageReader(io.BytesIO(sig_data))

        # 2. Charger le PDF original pour connaître la taille de la dernière page
        original_pdf = PdfReader(io.BytesIO(file_bytes))
        last_page = original_pdf.pages[-1]
        
        # Récupérer les dimensions réelles (MediaBox)
        width = float(last_page.mediabox.width)
        height = float(last_page.mediabox.height)

        # 3. Créer le calque (Overlay) à la TAILLE EXACTE de la page
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=(width, height))
        
        # Dessiner la signature (ajuste width/height selon tes besoins)
        # On utilise x et y fournis, mais attention au repère (0,0 est en bas à gauche)
        can.drawImage(sig_img, x, y, width=150, height=75, mask='auto', preserveAspectRatio=True)
        can.showPage() # Important pour finaliser la page
        can.save()
        packet.seek(0)
        
        overlay_pdf = PdfReader(packet)
        overlay_page = overlay_pdf.pages[0]

        # 4. Fusionner et générer le résultat
        writer = PdfWriter()

        for i, page in enumerate(original_pdf.pages):
            if i == len(original_pdf.pages) - 1:
                # Fusion de la signature sur la dernière page
                page.merge_page(overlay_page)
            writer.add_page(page)

        output = io.BytesIO()
        writer.write(output)
        output.seek(0)
        
        return output
    except Exception as e:
        print(f"DEBUG SIGNATURE: {e}")
        raise Exception(f"Erreur signature: {str(e)}")
