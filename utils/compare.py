import difflib
import pdfplumber
import os
from typing import Dict, List
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import red, green, black

class PDFComparer:
    def __init__(self, pdf1_path: str, pdf2_path: str):
        self.pdf1_path = pdf1_path
        self.pdf2_path = pdf2_path
    
    def compare_text(self) -> Dict:
        text1 = self._extract_text(self.pdf1_path)
        text2 = self._extract_text(self.pdf2_path)
        
        diff = difflib.unified_diff(
            text1.splitlines(),
            text2.splitlines(),
            fromfile='Original',
            tofile='Modified',
            lineterm=''
        )
        
        differences = list(diff)
        
        return {
            "has_differences": len(differences) > 0,
            "differences_count": len([d for d in differences if d.startswith('+') or d.startswith('-')]),
            "diff_lines": differences[:100],
            "similarity": self._calculate_similarity(text1, text2)
        }
    
    def compare_structure(self) -> Dict:
        with pdfplumber.open(self.pdf1_path) as pdf1:
            with pdfplumber.open(self.pdf2_path) as pdf2:
                return {
                    "pages_count_1": len(pdf1.pages),
                    "pages_count_2": len(pdf2.pages),
                    "pages_difference": abs(len(pdf1.pages) - len(pdf2.pages))
                }
    
    def generate_diff_pdf(self, output_path: str) -> str:
        try:
            c = canvas.Canvas(output_path, pagesize=A4)
            width, height = A4
            
            text1 = self._extract_text(self.pdf1_path)
            text2 = self._extract_text(self.pdf2_path)
            
            words1 = text1.split()
            words2 = text2.split()
            differ = difflib.SequenceMatcher(None, words1, words2)
            
            y_position = height - 50
            c.setFont("Helvetica", 8)
            
            for tag, i1, i2, j1, j2 in differ.get_opcodes():
                if y_position < 50:
                    c.showPage()
                    y_position = height - 50
                    c.setFont("Helvetica", 8)
                
                if tag == 'replace':
                    c.setFillColor(red)
                    c.drawString(50, y_position, f"[-] {' '.join(words1[i1:i2][:20])}")
                    y_position -= 12
                    c.setFillColor(green)
                    c.drawString(50, y_position, f"[+] {' '.join(words2[j1:j2][:20])}")
                elif tag == 'delete':
                    c.setFillColor(red)
                    c.drawString(50, y_position, f"[-] {' '.join(words1[i1:i2][:20])}")
                elif tag == 'insert':
                    c.setFillColor(green)
                    c.drawString(50, y_position, f"[+] {' '.join(words2[j1:j2][:20])}")
                elif tag == 'equal' and False:  # Ne pas afficher les parties égales
                    c.setFillColor(black)
                    c.drawString(50, y_position, f"   {' '.join(words1[i1:i2][:20])}")
                
                y_position -= 12
            
            c.save()
            return output_path
        except Exception as e:
            print(f"❌ Erreur génération PDF diff: {e}")
            return None
    
    def _extract_text(self, pdf_path: str) -> str:
        text = ""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except:
            pass
        return text
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        seq = difflib.SequenceMatcher(None, text1, text2)
        return seq.ratio() * 100

def handle_compare(pdf1_path: str, pdf2_path: str, output_dir: str) -> Dict:
    comparer = PDFComparer(pdf1_path, pdf2_path)
    
    text_diff = comparer.compare_text()
    struct_diff = comparer.compare_structure()
    
    diff_pdf = os.path.join(output_dir, "differences.pdf")
    comparer.generate_diff_pdf(diff_pdf)
    
    return {
        "text_differences": text_diff,
        "structural_differences": struct_diff,
        "diff_pdf": diff_pdf
    }