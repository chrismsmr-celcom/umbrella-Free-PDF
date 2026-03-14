import os
import subprocess
import sys

def handle_ocr(input_path, output_dir, language="fra"):
    try:
        base_name = os.path.basename(input_path)
        output_path = os.path.join(output_dir, f"ocr_{base_name}")

        # On garde l'essentiel pour éviter les erreurs de dépendances manquantes
        cmd = [
            sys.executable, "-m", "ocrmypdf",
            "--rotate-pages",  # Généralement géré nativement
            "--force-ocr",     # Force l'OCR même si du texte est détecté
            "-l", language,
            input_path,
            output_path
        ]

        # Utilisation de shell=True parfois nécessaire sur Windows pour appeler des modules
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0 and os.path.exists(output_path):
            return output_path
        else:
            print(f"DEBUG OCR ERROR: {result.stderr}")
            return None

    except Exception as e:
        print(f"SYSTEM ERROR durant l'OCR: {str(e)}")
        return None