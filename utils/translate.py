import os
import requests
import pdfplumber
import urllib.parse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

LIBRETRANSLATE_URL = os.getenv("LIBRETRANSLATE_URL", "https://libretranslate.de/translate")

async def handle_translation(input_path, temp_dir, target_lang, layout="text"):
    """
    Gère la traduction OS. 
    Note : 'layout' est ici simplifié pour Umbrella.
    """
    output_path = os.path.join(temp_dir, f"translated_{target_lang}.pdf")
    
    try:
        # 1. Extraction du texte
        text_content = ""
        with pdfplumber.open(input_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_content += page_text + "\n"

        if not text_content.strip():
            return None

        # 2. Traduction par blocs (indispensable pour les API gratuites)
        # On découpe pour éviter les erreurs de longueur d'URL (414)
        paragraphs = text_content.split('\n')
        translated_parts = []
        
        current_chunk = ""
        for p in paragraphs:
            if len(current_chunk) + len(p) < 1500: # Limite prudente pour Lingva
                current_chunk += p + "\n"
            else:
                translated_parts.append(await lingva_translate(current_chunk, target_lang))
                current_chunk = p + "\n"
        
        if current_chunk:
            translated_parts.append(await lingva_translate(current_chunk, target_lang))
            
        final_text = "".join(translated_parts)

        # 3. Reconstruction du PDF (Simple pour l'instant)
        return await generate_pdf_from_text(final_text, output_path)

    except Exception as e:
        print(f"❌ Erreur Traduction OS: {e}")
        return None

async def lingva_translate(text, target_lang):
    """Utilise l'API Lingva avec fallback"""
    if not text.strip(): return ""
    try:
        source_lang = "auto"
        encoded_text = urllib.parse.quote(text)
        url = f"https://lingva.ml/api/v1/{source_lang}/{target_lang}/{encoded_text}"
        
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json().get("translation", text)
    except Exception as e:
        print(f"⚠️ Lingva fail, essai LibreTranslate: {e}")
        return await libretranslate_request(text, target_lang)

async def libretranslate_request(text, target_lang):
    try:
        payload = {
            "q": text,
            "source": "auto",
            "target": target_lang,
            "format": "text"
        }
        r = requests.post(LIBRETRANSLATE_URL, json=payload, timeout=15)
        return r.json().get("translatedText", text)
    except:
        return text

async def generate_pdf_from_text(text, output_path):
    """Helper pour générer le PDF traduit proprement"""
    try:
        c = canvas.Canvas(output_path, pagesize=A4)
        width, height = A4
        text_object = c.beginText(50, height - 50)
        text_object.setFont("Helvetica", 10)
        
        for line in text.split('\n'):
            limit = 95
            for i in range(0, len(line), limit):
                text_object.textLine(line[i:i+limit])
            
            if text_object.getY() < 50:
                c.drawText(text_object)
                c.showPage()
                text_object = c.beginText(50, height - 50)
                text_object.setFont("Helvetica", 10)

        c.drawText(text_object)
        c.save()
        return output_path
    except Exception as e:
        print(f"❌ Erreur génération PDF: {e}")
        return None
