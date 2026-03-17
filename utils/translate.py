import os
import requests
import pdfplumber
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

# Si tu lances LibreTranslate en Docker sur ton serveur (ex: Render ou VPS)
# Remplace par "http://localhost:5000/translate" si c'est en local
LIBRETRANSLATE_URL = os.getenv("LIBRETRANSLATE_URL", "https://libretranslate.de/translate")

async def handle_translation(input_path, temp_dir, target_lang):
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

        # 2. Traduction via Lingva (Open Source API)
        # On peut switcher sur libretranslate_request si tu préfères ton Docker
        translated_text = await lingva_translate(text_content, target_lang)

        # 3. Reconstruction du PDF
        c = canvas.Canvas(output_path, pagesize=A4)
        width, height = A4
        text_object = c.beginText(50, height - 50)
        text_object.setFont("Helvetica", 10)
        
        for line in translated_text.split('\n'):
            # Découpage pour pas que ça dépasse du papier
            limit = 90
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
        print(f"❌ Erreur Traduction OS: {e}")
        return None

async def lingva_translate(text, target_lang):
    """Utilise l'API Lingva (Open Source)"""
    try:
        # Lingva limite parfois la taille par requête, on découpe par sécurité
        source_lang = "auto"
        # Nettoyage du texte pour l'URL
        import urllib.parse
        encoded_text = urllib.parse.quote(text[:2000]) # On limite à 2000 carcs par requête
        
        url = f"https://lingva.ml/api/v1/{source_lang}/{target_lang}/{encoded_text}"
        r = requests.get(url, timeout=10)
        res = r.json()
        return res.get("translation", text)
    except:
        # Si Lingva fail, on peut tenter LibreTranslate en local
        return await libretranslate_request(text, target_lang)

async def libretranslate_request(text, target_lang):
    """Utilise ton instance Docker LibreTranslate"""
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
