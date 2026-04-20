import os
import re
from typing import List, Tuple, Optional

class PDFRedactor:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
    
    def redact_text(self, text_to_redact: List[str], output_path: str) -> Optional[str]:
        try:
            from pikepdf import Pdf, Name, Array, String, Dictionary
            
            pdf = Pdf.open(self.pdf_path)
            
            for page in pdf.pages:
                if "/Annots" not in page:
                    page["/Annots"] = Array()
                
                for text in text_to_redact:
                    rect = self._find_text_rect(page, text)
                    if rect:
                        redact_annot = Dictionary({
                            Name("/Type"): Name("/Annot"),
                            Name("/Subtype"): Name("/Redact"),
                            Name("/Rect"): Array([rect[0], rect[1], rect[2], rect[3]]),
                            Name("/IC"): Array([0.0, 0.0, 0.0]),
                            Name("/Fill"): Array([0.0, 0.0, 0.0]),
                        })
                        page["/Annots"].append(redact_annot)
            
            pdf.save(output_path)
            return output_path
        except Exception as e:
            print(f"❌ Erreur masquage: {e}")
            return None
    
    def redact_regex(self, pattern: str, output_path: str) -> Optional[str]:
        try:
            import pdfplumber
            
            with pdfplumber.open(self.pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    words = page.extract_words()
                    for word in words:
                        if re.search(pattern, word.get('text', ''), re.IGNORECASE):
                            bbox = (word['x0'], word['top'], word['x1'], word['bottom'])
                            self.redact_area(page_num, bbox, output_path)
            
            return output_path
        except Exception as e:
            print(f"❌ Erreur masquage regex: {e}")
            return None
    
    def redact_area(self, page_num: int, bbox: Tuple[float, float, float, float], output_path: str) -> Optional[str]:
        try:
            from pikepdf import Pdf, Name, Array, Dictionary
            
            pdf = Pdf.open(self.pdf_path)
            
            if page_num <= len(pdf.pages):
                page = pdf.pages[page_num - 1]
                
                if "/Annots" not in page:
                    page["/Annots"] = Array()
                
                redact_annot = Dictionary({
                    Name("/Type"): Name("/Annot"),
                    Name("/Subtype"): Name("/Redact"),
                    Name("/Rect"): Array([bbox[0], bbox[1], bbox[2], bbox[3]]),
                    Name("/IC"): Array([0.0, 0.0, 0.0]),
                    Name("/Fill"): Array([0.0, 0.0, 0.0]),
                })
                page["/Annots"].append(redact_annot)
            
            pdf.save(output_path)
            return output_path
        except Exception as e:
            print(f"❌ Erreur masquage zone: {e}")
            return None
    
    def _find_text_rect(self, page, search_text: str) -> Optional[Tuple[float, float, float, float]]:
        try:
            import pdfplumber
            import tempfile
            
            temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
            
            from pikepdf import Pdf
            with Pdf.new() as new_pdf:
                new_pdf.pages.append(page)
                new_pdf.save(temp_pdf.name)
            
            with pdfplumber.open(temp_pdf.name) as pdf:
                if pdf.pages:
                    words = pdf.pages[0].extract_words()
                    for word in words:
                        if search_text.lower() in word.get('text', '').lower():
                            return (word['x0'], word['top'], word['x1'], word['bottom'])
            
            os.unlink(temp_pdf.name)
            return None
        except:
            return None

def handle_redact(input_path: str, output_dir: str, text_to_redact: List[str] = None, regex: str = None) -> Optional[str]:
    redactor = PDFRedactor(input_path)
    output_path = os.path.join(output_dir, "redacted.pdf")
    
    if regex:
        return redactor.redact_regex(regex, output_path)
    elif text_to_redact:
        return redactor.redact_text(text_to_redact, output_path)
    return None