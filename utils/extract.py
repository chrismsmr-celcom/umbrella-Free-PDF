from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
import io
from pypdf import PdfReader, PdfWriter

router = APIRouter(prefix="/organize", tags=["Organize"])

@router.post("/extract")
async def extract_pages(
    file: UploadFile = File(...), 
    pages: str = Form(...) # On reçoit "1,2,5" depuis le FormData JS
):
    """
    Extrait les pages sélectionnées d'un PDF.
    """
    try:
        # 1. Lecture du fichier en mémoire
        content = await file.read()
        pdf_reader = PdfReader(io.BytesIO(content))
        pdf_writer = PdfWriter()

        # 2. Parsing des pages envoyées par Umbrella JS
        try:
            # On convertit "1,2,5" en [0, 1, 4] (index 0 pour pypdf)
            page_indices = [int(p.strip()) - 1 for p in pages.split(",") if p.strip()]
        except ValueError:
            raise HTTPException(status_code=400, detail="Format de pages invalide.")

        # 3. Extraction
        total_pages = len(pdf_reader.pages)
        for idx in page_indices:
            if 0 <= idx < total_pages:
                pdf_writer.add_page(pdf_reader.pages[idx])
            else:
                # Optionnel : loguer l'erreur si l'index dépasse
                continue

        if len(pdf_writer.pages) == 0:
            raise HTTPException(status_code=400, detail="Aucune page valide à extraire.")

        # 4. Préparation du flux de sortie
        output_pdf = io.BytesIO()
        pdf_writer.write(output_pdf)
        output_pdf.seek(0)

        return StreamingResponse(
            output_pdf,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=extracted_{file.filename}"}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur Umbrella Engine: {str(e)}")

@router.post("/remove")
async def remove_pages(
    file: UploadFile = File(...), 
    pages: str = Form(...)
):
    """
    Supprime les pages sélectionnées (L'inverse de l'extraction).
    """
    try:
        content = await file.read()
        pdf_reader = PdfReader(io.BytesIO(content))
        pdf_writer = PdfWriter()

        # Pages à supprimer (indexées à 0)
        to_remove = [int(p.strip()) - 1 for p in pages.split(",") if p.strip()]
        
        for i in range(len(pdf_reader.pages)):
            if i not in to_remove:
                pdf_writer.add_page(pdf_reader.pages[i])

        output_pdf = io.BytesIO()
        pdf_writer.write(output_pdf)
        output_pdf.seek(0)

        return StreamingResponse(
            output_pdf,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=cleaned_{file.filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))