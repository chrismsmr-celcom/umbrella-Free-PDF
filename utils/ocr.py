import os
import subprocess
import pdfplumber
import tempfile
import time
from typing import Optional

def handle_ocr(input_path: str, output_dir: str, language: str = "fra") -> Optional[str]:
    """
    Applique l'OCR sur un PDF scanné avec gestion mémoire optimisée pour Render free
    """
    try:
        if not os.path.exists(input_path):
            print(f"Fichier introuvable: {input_path}")
            return None
        
        file_size = os.path.getsize(input_path)
        max_size = 100 * 1024 * 1024
        
        if file_size > max_size:
            print(f"Fichier trop volumineux pour l'OCR: {file_size // (1024*1024)}MB")
            return None
        
        output_path = os.path.join(output_dir, f"ocr_result_{int(time.time())}.pdf")
        
        # Correction: utiliser --redo-ocr au lieu de --force-ocr + --skip-text
        cmd = [
            "ocrmypdf",
            "--redo-ocr",            # Un seul flag au lieu de --force-ocr + --skip-text
            "--language", language,
            "--jobs", "1",
            "--output-type", "pdfa",
            "--optimize", "1",
            "--pdfa-image-compression", "jpeg",
            "--jpeg-quality", "75",
            "--tesseract-timeout", "60",
            "--continue-on-soft-render-error",
            input_path,
            output_path
        ]
        
        print(f"OCR en cours sur: {os.path.basename(input_path)}")
        
        start_time = time.time()
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=180,
            env={
                **os.environ,
                "OMP_THREAD_LIMIT": "1",
                "TESSERACT_THREADS": "1",
                "MAGICK_THREAD_LIMIT": "1"
            }
        )
        
        elapsed = time.time() - start_time
        
        if result.returncode in [0, 6] and os.path.exists(output_path):
            output_size = os.path.getsize(output_path)
            print(f"OCR termine en {elapsed:.1f}s ({output_size // 1024}KB)")
            return output_path
        else:
            print(f"OCRmyPDF Error (code {result.returncode}): {result.stderr[:500]}")
            return None
            
    except subprocess.TimeoutExpired:
        print(f"Timeout OCR apres 180 secondes")
        return None
    except Exception as e:
        print(f"SYSTEM ERROR OCR: {str(e)}")
        return None

def needs_ocr(pdf_path: str, threshold: int = 100) -> bool:
    """
    Detecte si un PDF a besoin d'OCR (est un scan)
    """
    try:
        if not os.path.exists(pdf_path):
            return True
        
        total_text = 0
        
        with pdfplumber.open(pdf_path) as pdf:
            pages_to_check = min(5, len(pdf.pages))
            
            for i in range(pages_to_check):
                page = pdf.pages[i]
                text = page.extract_text()
                
                if text:
                    char_count = sum(1 for c in text if c.isalnum())
                    total_text += char_count
                    
                    if total_text > threshold:
                        print(f"Texte detecte ({total_text} caracteres) - OCR non necessaire")
                        return False
        
        print(f"Scan detecte ({total_text} caracteres) - OCR necessaire")
        return total_text < threshold
        
    except Exception as e:
        print(f"Erreur detection OCR: {e}")
        return True

def get_text_content(pdf_path: str, max_pages: int = 10) -> str:
    """
    Extrait tout le texte d'un PDF pour l'analyse IA
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
        print(f"Erreur extraction texte: {e}")
        return ""

def optimize_ocr_result(input_path: str, output_dir: str) -> Optional[str]:
    """
    Optimise un PDF OCRise pour reduire sa taille
    """
    try:
        from pikepdf import Pdf
        
        output_path = os.path.join(output_dir, f"optimized_{os.path.basename(input_path)}")
        
        with Pdf.open(input_path) as pdf:
            pdf.save(
                output_path,
                compress_streams=True,
                stream_decode_level=1,
                object_stream_mode=1
            )
        
        original_size = os.path.getsize(input_path)
        new_size = os.path.getsize(output_path)
        
        if new_size < original_size:
            print(f"Optimisation OCR: {original_size//1024}KB -> {new_size//1024}KB")
            return output_path
        
        return input_path
        
    except Exception as e:
        print(f"Optimisation impossible: {e}")
        return input_path

def batch_ocr(pdf_paths: list, output_dir: str, language: str = "fra") -> list:
    """
    Traite plusieurs PDFs avec OCR en sequentiel (economie memoire)
    """
    results = []
    
    for i, pdf_path in enumerate(pdf_paths):
        print(f"OCR [{i+1}/{len(pdf_paths)}]: {os.path.basename(pdf_path)}")
        
        if needs_ocr(pdf_path):
            result = handle_ocr(pdf_path, output_dir, language)
            if result:
                results.append(result)
        else:
            results.append(pdf_path)
        
        import gc
        gc.collect()
    
    return results