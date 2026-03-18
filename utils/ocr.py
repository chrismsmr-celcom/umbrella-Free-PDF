import os
import subprocess
import pdfplumber

def handle_ocr(input_path, output_dir, language="fra"):
    try:
        output_path = os.path.join(output_dir, "ocr_result.pdf")

        cmd = [
            "ocrmypdf",
            "--skip-text", 
            "--rotate-pages",
            "--language", language, # Utilise le nom complet de l'argument
            "--jobs", "1",         # Important sur Render (évite de saturer le CPU/RAM)
            "--output-type", "pdf",
            input_path,
            output_path
        ]

        # On capture les erreurs pour le debug
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode in [0, 6]: 
            return output_path
        else:
            # Si ça échoue, on log le message d'erreur exact du binaire
            print(f"❌ OCRmyPDF Error: {result.stderr}")
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
