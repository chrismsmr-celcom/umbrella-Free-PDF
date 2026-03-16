import os
import subprocess

def handle_ocr(input_path, output_dir, language="fra"):
    try:
        output_path = os.path.join(output_dir, f"ocr_result.pdf")

        # Appel direct du binaire (plus fiable sur Linux/Render)
        cmd = [
            "ocrmypdf",
            "--skip-text", # Plus rapide si certaines pages ont déjà du texte
            "--rotate-pages",
            "-l", language,
            input_path,
            output_path
        ]

        # On utilise env pour s'assurer que le PATH est correct
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode in [0, 6]: # 6 = Déjà du texte, mais ok
            return output_path
        else:
            print(f"DEBUG OCR ERROR: {result.stderr}")
            return None
    except Exception as e:
        print(f"SYSTEM ERROR OCR: {e}")
        return None
