import os
import requests
import pdfplumber
import urllib.parse
import asyncio
import concurrent.futures
from typing import Optional, List
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import time

# Configuration
LIBRETRANSLATE_URL = os.getenv("LIBRETRANSLATE_URL", "https://libretranslate.de/translate")
LINGVA_URL = os.getenv("LINGVA_URL", "https://lingva.ml")
MAX_TEXT_LENGTH = 5000  # Maximum par requête API
BATCH_SIZE = 20  # Nombre de paragraphes par lot

async def handle_translation(input_path: str, temp_dir: str, target_lang: str, layout: str = "text") -> Optional[str]:
    """
    Gère la traduction d'un PDF avec fallback entre plusieurs API gratuites
    
    Args:
        input_path: Chemin du PDF source
        temp_dir: Dossier temporaire
        target_lang: Langue cible (en, fr, es, de, etc.)
        layout: 'layout' (conserve mise en page) ou 'text' (texte uniquement)
    
    Returns:
        Chemin du PDF traduit ou None
    """
    output_path = os.path.join(temp_dir, f"translated_{target_lang}_{int(time.time())}.pdf")
    
    try:
        # Vérifier que le fichier existe
        if not os.path.exists(input_path):
            print(f"❌ Fichier introuvable: {input_path}")
            return None
        
        # 1. Extraction du texte par pages
        print(f"📖 Extraction du texte du PDF...")
        pages_content = []
        total_pages = 0
        
        with pdfplumber.open(input_path) as pdf:
            total_pages = len(pdf.pages)
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text:
                    pages_content.append({
                        "page_num": i + 1,
                        "text": page_text.strip()
                    })
                else:
                    pages_content.append({
                        "page_num": i + 1,
                        "text": ""
                    })
        
        if not any(p["text"] for p in pages_content):
            print("❌ Aucun texte extractible du PDF")
            return None
        
        print(f"📄 {len([p for p in pages_content if p['text']])} pages avec texte détecté")
        
        # 2. Traduction du texte par lots
        print(f"🌐 Traduction vers {target_lang} en cours...")
        
        translated_pages = await translate_pdf_content(pages_content, target_lang)
        
        if not translated_pages:
            print("❌ Échec de la traduction")
            return None
        
        # 3. Reconstruction du PDF
        print(f"📝 Génération du PDF traduit...")
        
        if layout == "layout":
            # Version avec mise en page approximative
            result = await generate_pdf_with_layout(translated_pages, output_path)
        else:
            # Version texte uniquement
            result = await generate_pdf_text_only(translated_pages, output_path)
        
        if result and os.path.exists(output_path):
            print(f"✅ PDF traduit généré: {os.path.basename(output_path)}")
            return output_path
        
        return None
        
    except Exception as e:
        print(f"❌ Erreur Traduction: {str(e)}")
        return None

async def translate_pdf_content(pages_content: List[dict], target_lang: str) -> List[dict]:
    """
    Traduit le contenu du PDF page par page avec gestion des erreurs
    """
    translated_pages = []
    
    for page_info in pages_content:
        original_text = page_info["text"]
        
        if not original_text.strip():
            translated_pages.append({
                "page_num": page_info["page_num"],
                "text": ""
            })
            continue
        
        # Découper le texte en petits morceaux pour l'API
        chunks = split_text_into_chunks(original_text, MAX_TEXT_LENGTH)
        translated_chunks = []
        
        for chunk in chunks:
            translated = await translate_text_with_fallback(chunk, target_lang)
            translated_chunks.append(translated)
        
        translated_text = " ".join(translated_chunks)
        translated_pages.append({
            "page_num": page_info["page_num"],
            "text": translated_text
        })
        
        # Petit délai pour ne pas surcharger l'API
        await asyncio.sleep(0.5)
    
    return translated_pages

def split_text_into_chunks(text: str, max_length: int) -> List[str]:
    """
    Découpe le texte en chunks pour l'API
    """
    chunks = []
    paragraphs = text.split('\n')
    current_chunk = ""
    
    for para in paragraphs:
        if len(current_chunk) + len(para) + 1 <= max_length:
            if current_chunk:
                current_chunk += "\n" + para
            else:
                current_chunk = para
        else:
            if current_chunk:
                chunks.append(current_chunk)
            # Si un seul paragraphe est trop long, on le découpe
            if len(para) > max_length:
                words = para.split()
                temp_chunk = ""
                for word in words:
                    if len(temp_chunk) + len(word) + 1 <= max_length:
                        temp_chunk += " " + word if temp_chunk else word
                    else:
                        if temp_chunk:
                            chunks.append(temp_chunk)
                        temp_chunk = word
                if temp_chunk:
                    current_chunk = temp_chunk
                else:
                    current_chunk = ""
            else:
                current_chunk = para
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks

async def translate_text_with_fallback(text: str, target_lang: str) -> str:
    """
    Traduit un texte avec fallback entre plusieurs API
    """
    if not text.strip():
        return text
    
    # Essayer Lingva d'abord (gratuit, sans clé)
    try:
        result = await lingva_translate(text, target_lang)
        if result != text:
            return result
    except Exception as e:
        print(f"⚠️ Lingva échoué: {e}")
    
    # Fallback sur LibreTranslate
    try:
        result = await libretranslate_request(text, target_lang)
        if result != text:
            return result
    except Exception as e:
        print(f"⚠️ LibreTranslate échoué: {e}")
    
    # Fallback sur MyMemory (gratuit, sans clé)
    try:
        result = await mymemory_translate(text, target_lang)
        if result != text:
            return result
    except Exception as e:
        print(f"⚠️ MyMemory échoué: {e}")
    
    # Dernier recours : texte original
    print(f"⚠️ Aucune API disponible, texte non traduit")
    return text

async def lingva_translate(text: str, target_lang: str) -> str:
    """
    Utilise l'API Lingva (gratuit, sans clé)
    """
    try:
        source_lang = "auto"
        encoded_text = urllib.parse.quote(text[:2000])  # Limiter la longueur
        url = f"{LINGVA_URL}/api/v1/{source_lang}/{target_lang}/{encoded_text}"
        
        # Utiliser requests de manière synchrone dans un thread
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            response = await loop.run_in_executor(
                pool,
                lambda: requests.get(url, timeout=15, headers={"User-Agent": "UmbrellaPDF/1.0"})
            )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("translation", text)
        return text
        
    except Exception as e:
        print(f"⚠️ Erreur Lingva: {e}")
        return text

async def libretranslate_request(text: str, target_lang: str) -> str:
    """
    Utilise l'API LibreTranslate (gratuit, sans clé)
    """
    try:
        # Limiter la longueur du texte
        limited_text = text[:1000]
        
        payload = {
            "q": limited_text,
            "source": "auto",
            "target": target_lang,
            "format": "text"
        }
        
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            response = await loop.run_in_executor(
                pool,
                lambda: requests.post(LIBRETRANSLATE_URL, json=payload, timeout=15)
            )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("translatedText", text)
        return text
        
    except Exception as e:
        print(f"⚠️ Erreur LibreTranslate: {e}")
        return text

async def mymemory_translate(text: str, target_lang: str) -> str:
    """
    Utilise l'API MyMemory (gratuit, sans clé)
    """
    try:
        # Mapping des langues
        lang_map = {
            "fr": "fr|en",
            "en": "en|fr",
            "es": "es|en",
            "de": "de|en",
            "it": "it|en"
        }
        
        lang_pair = lang_map.get(target_lang, f"auto|{target_lang}")
        encoded_text = urllib.parse.quote(text[:500])
        url = f"https://api.mymemory.translated.net/get?q={encoded_text}&langpair={lang_pair}"
        
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            response = await loop.run_in_executor(
                pool,
                lambda: requests.get(url, timeout=10)
            )
        
        if response.status_code == 200:
            data = response.json()
            translated = data.get("responseData", {}).get("translatedText", text)
            return translated
        return text
        
    except Exception as e:
        print(f"⚠️ Erreur MyMemory: {e}")
        return text

async def generate_pdf_text_only(translated_pages: List[dict], output_path: str) -> bool:
    """
    Génère un PDF simple avec le texte traduit
    """
    try:
        c = canvas.Canvas(output_path, pagesize=A4)
        width, height = A4
        margin = 50
        y_position = height - margin
        font_size = 10
        line_height = font_size * 1.5
        
        c.setFont("Helvetica", font_size)
        
        for page_info in translated_pages:
            text = page_info["text"]
            
            if not text:
                c.showPage()
                c.setFont("Helvetica", font_size)
                y_position = height - margin
                continue
            
            # Découper le texte en lignes
            lines = []
            for paragraph in text.split('\n'):
                if paragraph.strip():
                    wrapped_lines = simpleSplit(paragraph, "Helvetica", font_size, width - 2 * margin)
                    lines.extend(wrapped_lines)
                else:
                    lines.append("")
            
            # Écrire les lignes sur la page
            for line in lines:
                if y_position < margin:
                    c.showPage()
                    c.setFont("Helvetica", font_size)
                    y_position = height - margin
                
                c.drawString(margin, y_position, line[:200])  # Limiter la longueur
                y_position -= line_height
            
            # Nouvelle page après chaque page
            if page_info["page_num"] < len(translated_pages):
                c.showPage()
                c.setFont("Helvetica", font_size)
                y_position = height - margin
        
        c.save()
        return True
        
    except Exception as e:
        print(f"❌ Erreur génération PDF texte: {e}")
        return False

async def generate_pdf_with_layout(translated_pages: List[dict], output_path: str) -> bool:
    """
    Génère un PDF avec une mise en page améliorée
    """
    try:
        c = canvas.Canvas(output_path, pagesize=A4)
        width, height = A4
        margin = 50
        y_position = height - margin
        font_size = 10
        line_height = font_size * 1.5
        
        c.setFont("Helvetica", font_size)
        
        for page_info in translated_pages:
            text = page_info["text"]
            
            if not text:
                c.showPage()
                c.setFont("Helvetica", font_size)
                y_position = height - margin
                continue
            
            # Ajouter l'en-tête de page
            c.setFont("Helvetica-Bold", 8)
            c.drawString(margin, margin - 10, f"Page {page_info['page_num']}")
            c.setFont("Helvetica", font_size)
            
            # Découper le texte en lignes
            for paragraph in text.split('\n'):
                if paragraph.strip():
                    wrapped_lines = simpleSplit(paragraph, "Helvetica", font_size, width - 2 * margin)
                    
                    for line in wrapped_lines:
                        if y_position < margin + 20:
                            c.showPage()
                            c.setFont("Helvetica", font_size)
                            y_position = height - margin
                            # Réafficher l'en-tête
                            c.setFont("Helvetica-Bold", 8)
                            c.drawString(margin, margin - 10, f"Page {page_info['page_num']}")
                            c.setFont("Helvetica", font_size)
                        
                        c.drawString(margin, y_position, line)
                        y_position -= line_height
                else:
                    y_position -= line_height / 2  # Espace entre paragraphes
            
            # Nouvelle page après chaque page originale
            if page_info["page_num"] < len(translated_pages):
                c.showPage()
                c.setFont("Helvetica", font_size)
                y_position = height - margin
        
        c.save()
        return True
        
    except Exception as e:
        print(f"❌ Erreur génération PDF layout: {e}")
        return False

# Fonction utilitaire pour vérifier si une langue est supportée
def is_language_supported(lang: str) -> bool:
    """
    Vérifie si la langue est supportée par les API
    """
    supported = ["en", "fr", "es", "de", "it", "pt", "ru", "zh", "ja", "ar"]
    return lang in supported

# Version batch pour plusieurs fichiers
async def batch_translate(pdf_paths: List[str], output_dir: str, target_lang: str) -> List[str]:
    """
    Traduit plusieurs PDFs en séquentiel
    """
    results = []
    
    for i, pdf_path in enumerate(pdf_paths):
        print(f"📄 Traduction [{i+1}/{len(pdf_paths)}]: {os.path.basename(pdf_path)}")
        result = await handle_translation(pdf_path, output_dir, target_lang)
        if result:
            results.append(result)
        
        # Pause entre les fichiers
        await asyncio.sleep(2)
    
    return results