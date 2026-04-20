# utils/__init__.py
from .core import cleanup, create_zip_on_disk
from .security import protect_pdf, unlock_pdf
from .sign_utils import process_pdf_signature
from .office import convert_to_pdf, pdf_to_word, pdf_to_excel, pdf_to_pptx, pdf_to_pdfa
from .html_to_pdf import handle_html_to_pdf
from .images import images_to_pdf, pdf_to_images
from .organize import handle_extract, handle_remove, handle_reorder
from .merge import handle_merge
from .split import handle_split
from .scan import handle_scan_effect
from .watermark import apply_watermark
from .repair import handle_repair
from .ocr import handle_ocr, needs_ocr, get_text_content
from .compress import handle_compress
from .edit import process_edit
from .translate import handle_translation
# from .ai import process_ai_task  # COMMENTÉ - Désactive l'IA si openai non installé

# NOUVEAUX MODULES
from .forms import FormExtractor, handle_form_extraction
from .redact import PDFRedactor, handle_redact
from .metadata import PDFMetadata, handle_get_metadata, handle_update_metadata
from .compare import PDFComparer, handle_compare
from .cache import pdf_cache

__all__ = [
    'cleanup', 'create_zip_on_disk',
    'protect_pdf', 'unlock_pdf',
    'process_pdf_signature',
    'convert_to_pdf', 'pdf_to_word', 'pdf_to_excel', 'pdf_to_pptx', 'pdf_to_pdfa',
    'handle_html_to_pdf',
    'images_to_pdf', 'pdf_to_images',
    'handle_extract', 'handle_remove', 'handle_reorder',
    'handle_merge',
    'handle_split',
    'handle_scan_effect',
    'apply_watermark',
    'handle_repair',
    'handle_ocr', 'needs_ocr', 'get_text_content',
    'handle_compress',
    'process_edit',
    'handle_translation',
    # 'process_ai_task',  # COMMENTÉ
    'FormExtractor', 'handle_form_extraction',
    'PDFRedactor', 'handle_redact',
    'PDFMetadata', 'handle_get_metadata', 'handle_update_metadata',
    'PDFComparer', 'handle_compare',
    'pdf_cache'
]