import os
import subprocess
import pdfplumber
import tempfile
import time
from typing import Optional

def handle_ocr(input_path: str, output_dir: str, language: str = "fra") -> Optional[str]:
    """
    Applique l'OCR sur un PDF scanné avec gestion mémoire optimisée pour Render free
    
    Args:
        input_path: Chemin du PDF source
        output_dir: Dossier de sortie
        language: Langue pour l'OCR (fra, eng, spa, etc.)
    
    Returns:
        Chemin du PDF OCRisé ou None en cas d'erreur
    """
    try:
        # Vérifier que le fichier existe
        if not os.path.exists(input_path):
            print(f"❌ Fichier introuvable: {input_path}")
            return None
        
        # Vérifier la taille du fichier
        file_size = os.path.getsize(input_path)
        max_size = 100 * 1024 * 1024  # 100MB max pour l'OCR
        
        if file_size > max_size:
            print(f"⚠️ Fichier trop volumineux pour l'OCR: {file_size // (1024*1024)}MB")
            return None
        
        output_path = os.path.join(output_dir, f"ocr_result_{int(time.time())}.pdf")
        
        # Optimisation des commandes pour Render free (RAM limitée)
        cmd = [
            "ocrmypdf",
            "--skip-text",           # Ignorer le texte existant
            "--language", language,
            "--jobs", "1",           # Un seul thread pour économiser la RAM
            "--output-type", "pdfa", # PDF/A pour meilleure compression
            "--optimize", "1",       # Niveau d'optimisation 1 (léger)
            "--pdfa-image-compression", "jpeg",
            "--jpeg-quality", "75",  # Compression raisonnable
            "--tesseract-timeout", "60",  # Timeout Tesseract 60 secondes
            "--tesseract-config", "load_system_dawg=0,load_freq_dawg=0", # Désactive certains dictionnaires
            "--continue-on-soft-render-error",
            "--force-ocr",           # Force l'OCR même si du texte existe
            input_path,
            output_path
        ]
        
        print(f"🔍 OCR en cours sur: {os.path.basename(input_path)}")
        
        # Exécution avec timeout et limitations mémoire
        start_time = time.time()
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=180,  # 3 minutes max
            env={
                **os.environ,
                "OMP_THREAD_LIMIT": "1",
                "TESSERACT_THREADS": "1",
                "MAGICK_THREAD_LIMIT": "1"
            }
        )
        
        elapsed = time.time() - start_time
        
        # Vérifier le résultat
        # Code 0 = succès, 6 = certaines pages n'ont pas de texte (acceptable)
        if result.returncode in [0, 6] and os.path.exists(output_path):
            output_size = os.path.getsize(output_path)
            print(f"✅ OCR terminé en {elapsed:.1f}s ({output_size // 1024}KB)")
            return output_path
        else:
            print(f"❌ OCRmyPDF Error (code {result.returncode}): {result.stderr[:500]}")
            return None
            
    except subprocess.TimeoutExpired:
        print(f"⏱️ Timeout OCR après 180 secondes")
        return None
    except Exception as e:
        print(f"❌ SYSTEM ERROR OCR: {str(e)}")
        return None

def needs_ocr(pdf_path: str, threshold: int = 100) -> bool:
    """
    Détecte si un PDF a besoin d'OCR (est un scan)
    
    Args:
        pdf_path: Chemin du PDF à analyser
        threshold: Nombre minimum de caractères pour considérer qu'il y a du texte
    
    Returns:
        True si le PDF a besoin d'OCR, False s'il contient déjà du texte
    """
    try:
        if not os.path.exists(pdf_path):
            return True
        
        total_text = 0
        
        with pdfplumber.open(pdf_path) as pdf:
            # Limiter l'analyse aux 5 premières pages pour économiser le temps
            pages_to_check = min(5, len(pdf.pages))
            
            for i in range(pages_to_check):
                page = pdf.pages[i]
                text = page.extract_text()
                
                if text:
                    # Compter les caractères alphanumériques
                    char_count = sum(1 for c in text if c.isalnum())
                    total_text += char_count
                    
                    # Si on trouve assez de texte, on arrête
                    if total_text > threshold:
                        print(f"📝 Texte détecté ({total_text} caractères) - OCR non nécessaire")
                        return False
        
        print(f"🔍 Scan détecté ({total_text} caractères) - OCR nécessaire")
        return total_text < threshold
        
    except Exception as e:
        print(f"⚠️ Erreur détection OCR: {e}")
        return True  # En cas de doute, on propose l'OCR

def get_text_content(pdf_path: str, max_pages: int = 10) -> str:
    """
    Extrait tout le texte d'un PDF pour l'analyse IA
    
    Args:
        pdf_path: Chemin du PDF
        max_pages: Nombre maximum de pages à extraire
    
    Returns:
        Texte extrait du PDF
    """
    try:
        all_text = []
        
        with pdfplumber.open(pdf_path) as pdf:
            pages_to_extract = min(max_pages, len(pdf.pages))
            
            for i in range(pages_to_extract):
                page = pdf.pages[i]
                text = page.extract_text()
                if text:
                    all_text.append(text)
        
        return "\n\n".join(all_text)
        
    except Exception as e:
        print(f"⚠️ Erreur extraction texte: {e}")
        return ""

def optimize_ocr_result(input_path: str, output_dir: str) -> Optional[str]:
    """
    Optimise un PDF OCRisé pour réduire sa taille
    
    Args:
        input_path: Chemin du PDF OCRisé
        output_dir: Dossier de sortie
    
    Returns:
        Chemin du PDF optimisé
    """
    try:
        from pikepdf import Pdf
        
        output_path = os.path.join(output_dir, f"optimized_{os.path.basename(input_path)}")
        
        with Pdf.open(input_path) as pdf:
            # Compression avancée
            pdf.save(
                output_path,
                compress_streams=True,
                stream_decode_level=1,
                object_stream_mode=1
            )
        
        original_size = os.path.getsize(input_path)
        new_size = os.path.getsize(output_path)
        
        if new_size < original_size:
            print(f"📦 Optimisation OCR: {original_size//1024}KB → {new_size//1024}KB")
            return output_path
        
        return input_path
        
    except Exception as e:
        print(f"⚠️ Optimisation impossible: {e}")
        return input_path

# Version batch pour traiter plusieurs PDFs
def batch_ocr(pdf_paths: list, output_dir: str, language: str = "fra") -> list:
    """
    Traite plusieurs PDFs avec OCR en séquentiel (économie mémoire)
    
    Args:
        pdf_paths: Liste des chemins de PDFs
        output_dir: Dossier de sortie
        language: Langue pour l'OCR
    
    Returns:
        Liste des PDFs OCRisés
    """
    results = []
    
    for i, pdf_path in enumerate(pdf_paths):
        print(f"📄 OCR [{i+1}/{len(pdf_paths)}]: {os.path.basename(pdf_path)}")
        
        if needs_ocr(pdf_path):
            result = handle_ocr(pdf_path, output_dir, language)
            if result:
                results.append(result)
        else:
            results.append(pdf_path)
        
        # Forcer le garbage collector après chaque fichier
        import gc
        gc.collect()
    
    return results