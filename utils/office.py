import subprocess
import os
import platform
import uuid
from pdf2docx import Converter
import pdfplumber
import pandas as pd
import pytesseract
from pdf2image import convert_from_path
import fitz  # PyMuPDF
from docx import Document
from pptx.util import Inches
from pptx import Presentation
import camelot

# --- CONFIGURATION OCR ---
if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def get_soffice_path():
    if platform.system() == "Windows":
        paths = [
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ]
        return next((p for p in paths if os.path.exists(p)), None)
    return "soffice"

# --- OFFICE -> PDF ---
def convert_to_pdf(input_path, output_dir):
    try:
        soffice = get_soffice_path()
        if not soffice: return None
        command = [soffice, "--headless", "--convert-to", "pdf", "--outdir", output_dir, input_path]
        subprocess.run(command, check=True, capture_output=True, timeout=60)
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        return os.path.join(output_dir, f"{base_name}.pdf")
    except Exception as e:
        print(f"❌ Erreur Office to PDF: {e}")
        return None

# --- PDF -> WORD (FIDÉLITÉ MAX) ---
def pdf_to_word(pdf_path, output_dir):
    try:
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        # On définit le chemin attendu
        output_path = os.path.join(output_dir, f"{base_name}.docx")
        
        # 1. Tentative avec pdf2docx (Meilleure fidélité structurelle)
        try:
            cv = Converter(pdf_path)
            cv.convert(output_path, start=0, end=None)
            cv.close()
            if os.path.exists(output_path): 
                return output_path
        except Exception as e:
            print(f"⚠️ pdf2docx a échoué, passage à LibreOffice: {e}")

        # 2. Secours avec LibreOffice
        soffice = get_soffice_path()
        if soffice:
            # IMPORTANT: LibreOffice utilise son propre nommage, on vérifie après
            subprocess.run([
                soffice, "--headless", "--invisible", 
                "--convert-to", "docx", 
                "--outdir", output_dir, 
                pdf_path
            ], check=True, capture_output=True)
            
            # On vérifie si le fichier existe bien là où LibreOffice l'a créé
            if os.path.exists(output_path):
                return output_path
                
        return None
    except Exception as e:
        print(f"❌ Erreur critique PDF to Word: {e}")
        return None

# --- PDF -> EXCEL (FIDÉLITÉ MAX) ---
def pdf_to_excel(pdf_path, output_dir):
    try:
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        output_path = os.path.join(output_dir, f"{base_name}.xlsx")
        
        # 1. Priorité Camelot
        try:
            tables = camelot.read_pdf(pdf_path, pages='all', flavor='lattice')
            if len(tables) == 0:
                tables = camelot.read_pdf(pdf_path, pages='all', flavor='stream')
            
            if len(tables) > 0:
                tables.export(output_path, f='excel')
                # Camelot crée parfois des fichiers nommés différemment, on vérifie
                return output_path
        except Exception as cam_e:
            print(f"⚠️ Camelot échoué: {cam_e}")

        # 2. Secours pdfplumber
        with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
            with pdfplumber.open(pdf_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    table = page.extract_table()
                    if table:
                        df = pd.DataFrame(table[1:], columns=table[0])
                        df.to_excel(writer, sheet_name=f"Page_{i+1}", index=False)
        return output_path
    except Exception as e:
        print(f"❌ Erreur PDF to Excel: {e}")
        return None

# --- PDF -> PPTX ---
def pdf_to_pptx(pdf_path, output_dir):
    try:
        # Sur Render, Poppler est dans le PATH, pas besoin de chemin Windows
        images = convert_from_path(pdf_path, dpi=200) 
        prs = Presentation()
        for i, image in enumerate(images):
            temp_img_path = os.path.join(output_dir, f"temp_{i}.jpg")
            image.save(temp_img_path, "JPEG")
            slide = prs.slides.add_slide(prs.slide_layouts[6])
            prs.slide_width = Inches(image.width / 200)
            prs.slide_height = Inches(image.height / 200)
            slide.shapes.add_picture(temp_img_path, 0, 0, width=prs.slide_width, height=prs.slide_height)
            os.remove(temp_img_path)
        
        out_pptx = os.path.join(output_dir, "output.pptx")
        prs.save(out_pptx)
        return out_pptx
    except Exception as e:
        print(f"❌ Erreur PPTX: {e}")
        return None

# --- PDF -> PDF/A ---
def pdf_to_pdfa(pdf_path, output_dir):
    try:
        output_path = os.path.join(output_dir, "archive.pdf")
        gs_exec = "gswin64c" if platform.system() == "Windows" else "gs"
        command = [
            gs_exec, "-dPDFA", "-dBATCH", "-dNOPAUSE", "-sDEVICE=pdfwrite",
            "-dPDFACompatibilityPolicy=1", f"-sOutputFile={output_path}", pdf_path
        ]
        subprocess.run(command, check=True, capture_output=True)
        return output_path
    except Exception as e:
        print(f"❌ Erreur PDF/A: {e}")
        return None
