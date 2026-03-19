import os
import subprocess
import pdfplumber

def handle_ocr(input_path, output_dir, language="fra"):
    try:
        output_path = os.path.join(output_dir, "ocr_result.pdf")
        
        cmd = [
            "ocrmypdf",
            "--skip-text",        # Ne pas refaire l'OCR si du texte existe déjà
            "--optimize", "1",    # Optimisation légère pour sauver de la RAM
            "--language", language,
            "--jobs", "1",         # FORCE 1 SEUL COEUR (Crucial sur Render)
            "--output-type", "pdf",
            "--tesseract-timeout", "300", # Laisse du temps au moteur
            input_path,
            output_path
        ]

        # Utilise env={"OMP_THREAD_LIMIT": "1"} pour limiter la librairie tesseract
        result = subprocess.run(cmd, capture_output=True, text=True, env={**os.environ, "OMP_THREAD_LIMIT": "1"})

        if result.returncode in [0, 6]: 
            return output_path
        else:
            print(f"❌ OCRmyPDF Error Log: {result.stderr}") # Regarde tes logs Render !
            return None
    except Exception as e:
        print(f"❌ SYSTEM ERROR OCR: {e}")
        return None
def needs_ocr(pdf_path):
    """Renvoie True si le PDF ne contient quasiment aucun texte extractible."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text and len(text.strip()) > 50: # Si on trouve + de 50 carcs, c'est du vrai texte
                    return False
        return True # Aucune page n'a de texte consistant -> C'est un scan
    except:
        return True
