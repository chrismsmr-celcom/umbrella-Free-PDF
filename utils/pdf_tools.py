import io
from PyPDF2 import PdfReader, PdfWriter

def remove_pdf_pages(input_pdf_bytes, pages_to_remove):
    """
    input_pdf_bytes: contenu du fichier en bytes
    pages_to_remove: liste d'entiers [1, 3, 5] (1-indexed)
    """
    reader = PdfReader(io.BytesIO(input_pdf_bytes))
    writer = PdfWriter()
    
    # On convertit en 0-indexed pour PyPDF2
    pages_to_remove_0 = [p - 1 for p in pages_to_remove]
    
    for i in range(len(reader.pages)):
        if i not in pages_to_remove_0:
            writer.add_page(reader.pages[i])
            
    output_stream = io.BytesIO()
    writer.write(output_stream)
    output_stream.seek(0)
    return output_stream