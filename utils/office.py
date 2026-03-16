import subprocess
import os
import platform
import uuid
from pdf2docx import Converter
import pdfplumber
import camelot
import pandas as pd
import tabula
import pytesseract
from pdf2image import convert_from_path
import fitz  # PyMuPDF
from docx import Document
from pptx.util import Inches
from pptx import Presentation

# --- CONFIGURATION OCR ---
# Assure-toi que ce chemin est correct sur ton PC
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def get_soffice_path():
    """Détecte automatiquement le chemin de LibreOffice"""
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

# --- ANALYSE ET OCR ---
def is_pdf_searchable(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        for page in doc:
            if page.get_text().strip():
                doc.close()
                return True
        doc.close()
        return False
    except:
        return False

def pdf_to_word_ocr(pdf_path, output_path):
    try:
        images = convert_from_path(pdf_path)
        doc = Document()
        for img in images:
            text = pytesseract.image_to_string(img, lang='fra')
            doc.add_paragraph(text)
        doc.save(output_path)
        return True
    except Exception as e:
        print(f"❌ Erreur OCR: {e}")
        return False

# --- PDF -> WORD ---
def pdf_to_word(pdf_path, output_dir):
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_path = os.path.join(output_dir, f"{base_name}.docx")
    
    # 1. Priorité : pdf2docx (Le meilleur pour la mise en page)
    try:
        cv = Converter(pdf_path)
        # multi_processing=True aide pour la vitesse sur Render
        cv.convert(output_path, start=0, end=None)
        cv.close()
        if os.path.exists(output_path): return output_path
    except:
        pass # On passe à la suite si ça échoue

    # 2. Secours : LibreOffice (Moins fidèle mais robuste)
    soffice = get_soffice_path()
    if soffice:
        # Commande pour forcer l'importation propre
        subprocess.run([soffice, "--headless", "--convert-to", "docx", "--outdir", output_dir, pdf_path])
        return output_path

        cv = Converter(pdf_path)
        cv.convert(output_path, lattice_threshold=15, multi_processing=True)
        cv.close()
        return output_path if os.path.exists(output_path) else None
    except Exception as e:
        print(f"❌ Erreur PDF to Word: {e}")
        return None

# --- PDF -> EXCEL ---
def pdf_to_excel(pdf_path, output_dir):
    """
    Convertit un PDF en Excel avec une fidélité maximale.
    Priorise Camelot pour la précision structurelle.
    """
    try:
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        output_path = os.path.join(output_dir, f"{base_name}.xlsx")
        
        # --- ÉTAPE 1 : ESSAI AVEC CAMELOT (Fidélité Haute Précision) ---
        # Camelot analyse les lignes (lattice) et les espaces (stream)
        try:
            # On tente d'abord 'lattice' (idéal pour les tableaux avec des bordures visibles)
            tables = camelot.read_pdf(pdf_path, pages='all', flavor='lattice')
            
            # Si aucune table avec bordure, on tente 'stream' (tableaux sans lignes)
            if len(tables) == 0:
                tables = camelot.read_pdf(pdf_path, pages='all', flavor='stream')
            
            if len(tables) > 0:
                # Export direct vers Excel via Camelot
                tables.export(output_path, f='excel')
                # Camelot génère parfois des noms comme output.xlsx, on renomme si besoin
                if os.path.exists(output_path):
                    return output_path
        except Exception as cam_err:
            print(f"⚠️ Camelot a échoué, passage au moteur de secours: {cam_err}")

        # --- ÉTAPE 2 : REPLI SUR PDFPLUMBER (Fidélité de Secours) ---
        all_tables_found = False
        
        with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
            with pdfplumber.open(pdf_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    # Configuration avancée pour pdfplumber
                    table = page.extract_table({
                        "vertical_strategy": "lines", 
                        "horizontal_strategy": "lines",
                        "snap_tolerance": 3,
                    })
                    
                    if not table:
                        table = page.extract_table() # Tentative automatique
                    
                    if table:
                        all_tables_found = True
                        # Nettoyage des données pour éviter les décalages de colonnes
                        df = pd.DataFrame(table[1:], columns=table[0])
                        df = df.dropna(how='all').dropna(axis=1, how='all')
                        
                        # Nettoyage des caractères spéciaux qui font planter Excel
                        df = df.applymap(lambda x: x.encode('unicode_escape').decode('utf-8') if isinstance(x, str) else x)
                        
                        sheet_name = f"Page_{i+1}"
                        df.to_excel(writer, sheet_name=sheet_name[:31], index=False)
            
            if not all_tables_found:
                df_info = pd.DataFrame([["Aucun tableau structurel n'a été détecté."]])
                df_info.to_excel(writer, sheet_name="Info", index=False, header=False)

        return output_path

    except Exception as e:
        print(f"❌ Erreur critique PDF to Excel: {e}")
        return None
# --- PDF -> PPTX ---
def pdf_to_pptx(pdf_path, output_dir):
    try:
        # Chemin vers ton Poppler bin
        POPPLER_PATH = r"C:\Users\USER\Downloads\Release-25.12.0-0\poppler-25.12.0\Library\bin"
        
        # 1. Conversion du PDF en images en utilisant Poppler
        images = convert_from_path(pdf_path, dpi=200, poppler_path=POPPLER_PATH) 
        
        prs = Presentation()
        
        if images:
            img_w, img_h = images[0].size
            prs.slide_width = Inches(img_w / 200)
            prs.slide_height = Inches(img_h / 200)

        for i, image in enumerate(images):
            temp_img_path = os.path.join(output_dir, f"page_{i}.jpg")
            image.save(temp_img_path, "JPEG", quality=80)
            
            slide = prs.slides.add_slide(prs.slide_layouts[6])
            slide.shapes.add_picture(temp_img_path, 0, 0, width=prs.slide_width, height=prs.slide_height)
            
            os.remove(temp_img_path)

        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        output_path = os.path.join(output_dir, f"{base_name}.pptx")
        prs.save(output_path)
        
        return output_path
    except Exception as e:
        print(f"❌ Erreur Conversion PPTX : {e}")
        return None        
# --- PDF -> PDF/A ---
def pdf_to_pdfa(pdf_path, output_dir):
    try:
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        output_path = os.path.join(output_dir, f"{base_name}_archive.pdf")
        
        # 1. Détecter le chemin de Ghostscript
        # Si tu ne l'as pas mis dans ton PATH Windows, mets le chemin complet ici :
        gs_exec = "gswin64c" if platform.system() == "Windows" else "gs"
        
        # 2. Commande Ghostscript pour PDF/A-2b (le plus compatible)
        command = [
            gs_exec,
            "-dPDFA",
            "-dBATCH",
            "-dNOPAUSE",
            "-dNOOUTERSAVE",
            "-dColorConversionStrategy=/RGB",
            "-sDEVICE=pdfwrite",
            "-dPDFACompatibilityPolicy=1",
            f"-sOutputFile={output_path}",
            pdf_path
        ]
        
        # 3. Exécution
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ Erreur Ghostscript : {result.stderr}")
            return None
            
        return output_path if os.path.exists(output_path) else None
        
    except Exception as e:
        print(f"❌ Erreur Conversion PDF/A : {e}")
        return None
