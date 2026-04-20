import pdfplumber
import json
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import os

@dataclass
class FormField:
    """Représente un champ de formulaire"""
    name: str
    value: str
    type: str
    page: int
    bbox: tuple

class FormExtractor:
    """Extracteur de formulaires PDF"""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.fields = []
        
    def extract_all_fields(self) -> List[FormField]:
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    if page.annots:
                        for annot in page.annots:
                            field = self._parse_annotation(annot, page_num)
                            if field:
                                self.fields.append(field)
                    
                    text = page.extract_text() or ""
                    self._detect_text_fields(text, page_num)
            
            return self.fields
        except Exception as e:
            print(f"❌ Erreur extraction formulaire: {e}")
            return []
    
    def _parse_annotation(self, annot: dict, page_num: int) -> Optional[FormField]:
        try:
            field_type = annot.get("/FT", "")
            field_name = annot.get("/T", "").replace("(", "").replace(")", "")
            field_value = annot.get("/V", "")
            rect = annot.get("/Rect", [0, 0, 0, 0])
            
            type_mapping = {
                "/Tx": "text",
                "/Btn": "checkbox",
                "/Sig": "signature",
                "/Ch": "choice"
            }
            
            return FormField(
                name=field_name,
                value=str(field_value),
                type=type_mapping.get(field_type, "unknown"),
                page=page_num,
                bbox=tuple(rect)
            )
        except:
            return None
    
    def _detect_text_fields(self, text: str, page_num: int):
        patterns = [
            (r"Nom\s*:\s*([^\n]+)", "nom"),
            (r"Prénom\s*:\s*([^\n]+)", "prenom"),
            (r"Email\s*:\s*([^\n]+)", "email"),
            (r"Téléphone\s*:\s*([^\n]+)", "telephone"),
        ]
        
        for pattern, field_name in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                self.fields.append(FormField(
                    name=field_name,
                    value=match.group(1).strip(),
                    type="detected",
                    page=page_num,
                    bbox=(0, 0, 0, 0)
                ))
    
    def to_json(self, output_path: str) -> str:
        data = [asdict(field) for field in self.fields]
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return output_path

def handle_form_extraction(input_path: str, output_dir: str) -> Dict:
    extractor = FormExtractor(input_path)
    fields = extractor.extract_all_fields()
    
    json_path = os.path.join(output_dir, "form_fields.json")
    extractor.to_json(json_path)
    
    return {
        "total_fields": len(fields),
        "fields": [asdict(f) for f in fields],
        "json_file": json_path
    }