import os
import json
from datetime import datetime
from typing import Dict, Any, Optional
from pikepdf import Pdf, Name, String

class PDFMetadata:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
    
    def read_all(self) -> Dict[str, Any]:
        metadata = {
            "file_name": os.path.basename(self.pdf_path),
            "file_size": os.path.getsize(self.pdf_path),
        }
        
        try:
            with Pdf.open(self.pdf_path) as pdf:
                metadata["num_pages"] = len(pdf.pages)
                
                if pdf.doc_info:
                    for key, value in pdf.doc_info.items():
                        clean_key = str(key).replace("/", "")
                        metadata[clean_key] = str(value)
        except Exception as e:
            print(f"⚠️ Erreur lecture métadonnées: {e}")
        
        return metadata
    
    def update(self, metadata: Dict[str, Any], output_path: str) -> Optional[str]:
        try:
            with Pdf.open(self.pdf_path) as pdf:
                for key, value in metadata.items():
                    pdf_key = Name(f"/{key}")
                    pdf.doc_info[pdf_key] = String(str(value))
                
                # Ajouter date de modification
                now = datetime.now()
                pdf.doc_info[Name("/ModDate")] = String(f"D:{now.strftime('%Y%m%d%H%M%S')}")
                
                pdf.save(output_path)
            return output_path
        except Exception as e:
            print(f"❌ Erreur mise à jour métadonnées: {e}")
            return None
    
    def remove_metadata(self, output_path: str) -> Optional[str]:
        try:
            with Pdf.open(self.pdf_path) as pdf:
                pdf.doc_info.clear()
                pdf.save(output_path)
            return output_path
        except Exception as e:
            print(f"❌ Erreur suppression métadonnées: {e}")
            return None

def handle_get_metadata(input_path: str, output_dir: str) -> Dict:
    handler = PDFMetadata(input_path)
    result = handler.read_all()
    
    json_path = os.path.join(output_dir, "metadata.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    return result

def handle_update_metadata(input_path: str, output_dir: str, metadata: Dict[str, str]) -> Optional[str]:
    handler = PDFMetadata(input_path)
    output_path = os.path.join(output_dir, "updated_metadata.pdf")
    return handler.update(metadata, output_path)