from fastapi import FastAPI, UploadFile, File, HTTPException, Form, BackgroundTasks, Request
from fastapi.responses import FileResponse, StreamingResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import List
from utils.security import protect_pdf
import tempfile, os, shutil, uuid
from PIL import Image
from fastapi import Form
import io
import mimetypes
import uuid
from fastapi import HTTPException
from fastapi import UploadFile, File, Form
from fastapi.responses import StreamingResponse
from utils.sign_utils import process_pdf_signature # Ton nouvel utilitaire

# Import des modules locaux
from utils.core import cleanup, create_zip_on_disk
# Ligne 15 corrigée
from utils.office import convert_to_pdf, pdf_to_word, pdf_to_excel, pdf_to_pptx, pdf_to_pdfa
from utils.images import images_to_pdf, pdf_to_images
from utils.organize import handle_extract, handle_remove, handle_reorder
from utils.merge import handle_merge
from utils.split import handle_split
from utils.scan import handle_scan_effect
from utils.watermark import apply_watermark
from utils.repair import handle_repair
from utils.ocr import handle_ocr
from utils.compress import handle_compress
from utils.html_to_pdf import handle_html_to_pdf

app = FastAPI(title="Umbrella PDF Engine PRO")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

scan_sessions = {}

# --- LOGIQUE GÉNÉRIQUE BATCH ---

def handle_batch_response(processed_files, background_tasks, temp_dir):
    """Gère le renvoi d'un fichier unique ou d'un ZIP de manière sécurisée."""
    
    if not processed_files:
        background_tasks.add_task(cleanup, temp_dir)
        raise HTTPException(status_code=500, detail="Aucun fichier n'a pu être traité.")

    # 1. Application du filigrane
    for f_path in processed_files:
        if f_path.lower().endswith(".pdf"):
            try:
                apply_watermark(f_path)
            except Exception as e:
                print(f"⚠️ Warning Watermark: {e}")

    # 2. Préparation de la réponse
    try:
        # CAS 1 : Plusieurs fichiers -> On crée un ZIP PHYSIQUE sur le disque
        if len(processed_files) > 1:
            zip_filename = f"umbrella_pack_{uuid.uuid4().hex[:5]}.zip"
            zip_path = os.path.join(temp_dir, zip_filename)
            
            # Utilise une fonction qui écrit le ZIP sur le disque (plus stable que StreamingResponse)
            create_zip_on_disk(processed_files, zip_path)
            
            # On utilise FileResponse avec le background task intégré
            return FileResponse(
                zip_path,
                media_type="application/zip",
                filename=zip_filename,
                background=background_tasks.add_task(cleanup, temp_dir)
            )

        # CAS 2 : Un seul fichier
        else:
            file_to_send = processed_files[0]
            if not os.path.exists(file_to_send):
                raise FileNotFoundError
                
            filename = os.path.basename(file_to_send)
            mime_type, _ = mimetypes.guess_type(file_to_send)
            
            return FileResponse(
                file_to_send,
                media_type=mime_type or "application/octet-stream",
                filename=filename,
                background=background_tasks.add_task(cleanup, temp_dir)
            )

    except Exception as e:
        background_tasks.add_task(cleanup, temp_dir)
        print(f"❌ Erreur lors de la réponse: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne lors de la génération du téléchargement.")
# --- ROUTES D'ORGANISATION ---

@app.post("/organize/merge")
async def merge_endpoint(background_tasks: BackgroundTasks, files: List[UploadFile] = File(...)):
    temp_dir = tempfile.mkdtemp()
    try:
        paths = []
        for file in files:
            p = os.path.join(temp_dir, f"{uuid.uuid4().hex[:5]}_{file.filename}")
            with open(p, "wb") as f:
                shutil.copyfileobj(file.file, f)
            paths.append(p)
        result = handle_merge(paths, temp_dir)
        if result:
            apply_watermark(result)
            background_tasks.add_task(cleanup, temp_dir)
            return FileResponse(result, filename="umbrella_merged.pdf")
        raise Exception("Échec de la fusion")
    except Exception as e:
        cleanup(temp_dir)
        raise HTTPException(500, detail=str(e))

@app.post("/organize/split")
async def split_endpoint(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    temp_dir = tempfile.mkdtemp()
    try:
        in_p = os.path.join(temp_dir, file.filename)
        with open(in_p, "wb") as f:
            shutil.copyfileobj(file.file, f)
        processed_files = handle_split(in_p, temp_dir)
        return handle_batch_response(processed_files, background_tasks, temp_dir)
    except Exception as e:
        cleanup(temp_dir)
        raise HTTPException(500, detail=str(e))

@app.post("/organize/reorder")
async def reorder_endpoint(background_tasks: BackgroundTasks, file: UploadFile = File(...), pages: str = Form(...)):
    temp_dir = tempfile.mkdtemp()
    try:
        in_p = os.path.join(temp_dir, file.filename)
        with open(in_p, "wb") as f:
            shutil.copyfileobj(file.file, f)
        result = handle_reorder(in_p, pages, temp_dir)
        if result:
            apply_watermark(result)
            background_tasks.add_task(cleanup, temp_dir)
            return FileResponse(result, filename=f"reordered_{file.filename}")
        raise HTTPException(400, "Erreur lors du réordonnancement.")
    except Exception as e:
        cleanup(temp_dir)
        raise HTTPException(500, detail=str(e))

@app.post("/organize/extract")
async def extract_endpoint(background_tasks: BackgroundTasks, file: UploadFile = File(...), pages: str = Form(...)):
    temp_dir = tempfile.mkdtemp()
    try:
        in_p = os.path.join(temp_dir, file.filename)
        with open(in_p, "wb") as f:
            shutil.copyfileobj(file.file, f)
        result = handle_extract(in_p, pages, temp_dir)
        if result:
            apply_watermark(result)
            background_tasks.add_task(cleanup, temp_dir)
            return FileResponse(result, filename=f"extracted_{file.filename}")
        raise HTTPException(400, "Erreur lors de l'extraction.")
    except Exception as e:
        cleanup(temp_dir)
        raise HTTPException(500, detail=str(e))

@app.post("/organize/remove")
async def remove_endpoint(background_tasks: BackgroundTasks, file: UploadFile = File(...), pages: str = Form(...)):
    temp_dir = tempfile.mkdtemp()
    try:
        in_p = os.path.join(temp_dir, file.filename)
        with open(in_p, "wb") as f:
            shutil.copyfileobj(file.file, f)
        result = handle_remove(in_p, pages, temp_dir)
        if result:
            apply_watermark(result)
            background_tasks.add_task(cleanup, temp_dir)
            return FileResponse(result, filename=f"cleaned_{file.filename}")
        raise HTTPException(400, "Erreur lors de la suppression.")
    except Exception as e:
        cleanup(temp_dir)
        raise HTTPException(500, detail=str(e))

# --- SCAN MOBILE ---

@app.get("/scan/generate-session")
async def generate_scan_session(request: Request):
    session_id = uuid.uuid4().hex[:8]
    scan_sessions[session_id] = None
    host_url = f"{request.url.scheme}://{request.url.netloc}"
    return {"session_id": session_id, "url": f"{host_url}/mobile-scan?s={session_id}"}

@app.get("/mobile-scan", response_class=HTMLResponse)
async def serve_mobile_scan_page(s: str):
    if os.path.exists("mobile_scan.html"):
        with open("mobile_scan.html", "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Erreur : Fichier mobile_scan.html introuvable</h1>"

@app.post("/scan/upload-mobile/{session_id}")
async def upload_from_mobile(session_id: str, file: UploadFile = File(...)):
    if session_id not in scan_sessions:
        raise HTTPException(404, "Session expirée ou invalide")
    storage_dir = os.path.join(tempfile.gettempdir(), "umbrella_scans")
    os.makedirs(storage_dir, exist_ok=True)
    in_p = os.path.join(storage_dir, f"scan_{session_id}_{file.filename}")
    with open(in_p, "wb") as f:
        shutil.copyfileobj(file.file, f)
    scanned_pdf = handle_scan_effect(in_p, storage_dir)
    scan_sessions[session_id] = scanned_pdf
    return {"status": "success", "message": "Fichier traité"}

@app.get("/scan/check-session/{session_id}")
async def check_session(session_id: str):
    file_path = scan_sessions.get(session_id)
    if file_path and os.path.exists(file_path):
        return {"ready": True, "filename": os.path.basename(file_path)}
    return {"ready": False}

@app.get("/scan/get-result/{filename}")
async def get_scan_result(filename: str, background_tasks: BackgroundTasks):
    file_path = os.path.join(tempfile.gettempdir(), "umbrella_scans", filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="application/pdf")
    raise HTTPException(404, "Fichier introuvable")

# --- ÉDITION & RÉPARATION ---

@app.post("/edit/compress")
async def compress_endpoint(background_tasks: BackgroundTasks, file: UploadFile = File(...), quality: str = Form("medium")):
    temp_dir = tempfile.mkdtemp()
    try:
        in_p = os.path.join(temp_dir, file.filename)
        with open(in_p, "wb") as f:
            shutil.copyfileobj(file.file, f)
        result = handle_compress(in_p, temp_dir, quality)
        if result:
            apply_watermark(result)
            background_tasks.add_task(cleanup, temp_dir)
            return FileResponse(result, filename=f"compressed_{file.filename}")
        raise HTTPException(400, "Échec compression")
    except Exception as e:
        cleanup(temp_dir)
        raise HTTPException(500, detail=str(e))

@app.post("/edit/repair")
async def repair_endpoint(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    temp_dir = tempfile.mkdtemp()
    try:
        in_p = os.path.join(temp_dir, file.filename)
        with open(in_p, "wb") as f:
            shutil.copyfileobj(file.file, f)
        result = handle_repair(in_p, temp_dir)
        if result:
            apply_watermark(result)
            background_tasks.add_task(cleanup, temp_dir)
            return FileResponse(result, filename="umbrella_repaired.pdf")
        raise HTTPException(400, "PDF trop endommagé")
    except Exception as e:
        cleanup(temp_dir)
        raise HTTPException(500, detail=str(e))

# --- CONVERSION ---

@app.post("/convert/office-to-pdf")
async def office_to_pdf_endpoint(background_tasks: BackgroundTasks, files: List[UploadFile] = File(...)):
    temp_dir = tempfile.mkdtemp()
    processed_files = []
    try:
        for file in files:
            in_p = os.path.join(temp_dir, file.filename)
            with open(in_p, "wb") as f:
                shutil.copyfileobj(file.file, f)
            result = convert_to_pdf(in_p, temp_dir)
            if result and os.path.exists(result):
                processed_files.append(result)
        return handle_batch_response(processed_files, background_tasks, temp_dir)
    except Exception as e:
        cleanup(temp_dir)
        raise HTTPException(500, detail=str(e))

@app.post("/convert/pdf-to-word")
async def pdf_to_word_endpoint(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    temp_dir = tempfile.mkdtemp()
    try:
        in_p = os.path.join(temp_dir, file.filename)
        with open(in_p, "wb") as f:
            shutil.copyfileobj(file.file, f)
        result = pdf_to_word(in_p, temp_dir)
        if result and os.path.exists(result):
            return handle_batch_response([result], background_tasks, temp_dir)
        raise HTTPException(400, "La conversion Word a échoué.")
    except Exception as e:
        cleanup(temp_dir)
        raise HTTPException(500, detail=str(e))

@app.post("/convert/pdf-to-excel")
async def pdf_to_excel_endpoint(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    temp_dir = tempfile.mkdtemp()
    try:
        in_p = os.path.join(temp_dir, file.filename)
        with open(in_p, "wb") as f:
            shutil.copyfileobj(file.file, f)
        result = pdf_to_excel(in_p, temp_dir)
        if result and os.path.exists(result):
            return handle_batch_response([result], background_tasks, temp_dir)
        raise HTTPException(400, "Échec conversion Excel")
    except Exception as e:
        cleanup(temp_dir)
        raise HTTPException(500, detail=str(e))

@app.post("/convert/pdf-to-pptx")
async def pdf_to_pptx_endpoint(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    temp_dir = tempfile.mkdtemp()
    try:
        in_p = os.path.join(temp_dir, file.filename)
        with open(in_p, "wb") as f:
            shutil.copyfileobj(file.file, f)
        result = pdf_to_pptx(in_p, temp_dir)
        if result and os.path.exists(result):
            return handle_batch_response([result], background_tasks, temp_dir)
        raise HTTPException(400, "La conversion PowerPoint a échoué.")
    except Exception as e:
        cleanup(temp_dir)
        raise HTTPException(500, detail=str(e))

@app.post("/convert/html-to-pdf")
async def html_to_pdf_endpoint(background_tasks: BackgroundTasks, file: UploadFile = File(None), html_content: str = Form(None)):
    temp_dir = tempfile.mkdtemp()
    try:
        input_data = None
        if file and file.filename:
            in_p = os.path.join(temp_dir, file.filename)
            with open(in_p, "wb") as f:
                shutil.copyfileobj(file.file, f)
            input_data = in_p
        elif html_content:
            input_data = html_content
        else:
            raise HTTPException(400, "Aucun contenu HTML fourni.")
        result = handle_html_to_pdf(input_data, temp_dir)
        if result and os.path.exists(result):
            apply_watermark(result)
            background_tasks.add_task(cleanup, temp_dir)
            return FileResponse(result, filename="umbrella_converted.pdf", media_type="application/pdf")
        raise HTTPException(400, "Erreur de conversion HTML.")
    except Exception as e:
        cleanup(temp_dir)
        raise HTTPException(500, detail=str(e))

@app.post("/convert/ocr")
async def ocr_endpoint(background_tasks: BackgroundTasks, file: UploadFile = File(...), language: str = Form("fra")):
    temp_dir = tempfile.mkdtemp()
    try:
        in_p = os.path.join(temp_dir, file.filename)
        with open(in_p, "wb") as f:
            shutil.copyfileobj(file.file, f)
        result = handle_ocr(in_p, temp_dir, language)
        if result and os.path.exists(result):
            apply_watermark(result)
            background_tasks.add_task(cleanup, temp_dir)
            return FileResponse(result, filename=f"searchable_{file.filename}", media_type="application/pdf")
        raise HTTPException(400, "OCR échoué")
    except Exception as e:
        cleanup(temp_dir)
        raise HTTPException(500, detail=str(e))

@app.post("/convert/images-to-pdf")
async def images_to_pdf_endpoint(background_tasks: BackgroundTasks, files: List[UploadFile] = File(...)):
    temp_dir = tempfile.mkdtemp()
    try:
        paths = []
        for file in files:
            p = os.path.join(temp_dir, f"{uuid.uuid4().hex[:5]}_{file.filename}")
            with open(p, "wb") as f:
                shutil.copyfileobj(file.file, f)
            paths.append(p)
        output_pdf = os.path.join(temp_dir, "umbrella_images.pdf")
        result = images_to_pdf(paths, output_pdf)
        if result and os.path.exists(result):
            apply_watermark(result)
            background_tasks.add_task(cleanup, temp_dir)
            return FileResponse(result, filename="umbrella_images.pdf")
        raise HTTPException(400, "Échec images-to-pdf")
    except Exception as e:
        cleanup(temp_dir)
        raise HTTPException(500, detail=str(e))

@app.post("/convert/pdf-to-jpg")
async def pdf_to_jpg_endpoint(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    temp_dir = tempfile.mkdtemp()
    try:
        in_p = os.path.join(temp_dir, file.filename)
        with open(in_p, "wb") as f:
            shutil.copyfileobj(file.file, f)
        processed_files = pdf_to_images(in_p, temp_dir)
        return handle_batch_response(processed_files, background_tasks, temp_dir)
    except Exception as e:
        cleanup(temp_dir)
        raise HTTPException(500, detail=str(e))
        
@app.post("/edit/pdf-to-pdfa")
async def pdf_to_pdfa_endpoint(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    temp_dir = tempfile.mkdtemp()
    try:
        in_p = os.path.join(temp_dir, file.filename)
        with open(in_p, "wb") as f:
            shutil.copyfileobj(file.file, f)
            
        result = pdf_to_pdfa(in_p, temp_dir)
        
        if result and os.path.exists(result):
            return handle_batch_response([result], background_tasks, temp_dir)
        
        raise HTTPException(status_code=400, detail="Échec de l'archivage PDF/A.")
    except Exception as e:
        cleanup(temp_dir)
        print(f"❌ Erreur Route PDF/A: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
@app.post("/security/protect")
async def protect_pdf_endpoint(
    background_tasks: BackgroundTasks, 
    file: UploadFile = File(...), 
    password: str = Form(...) # Le mot de passe envoyé par le modale
):
    temp_dir = tempfile.mkdtemp()
    try:
        in_p = os.path.join(temp_dir, file.filename)
        with open(in_p, "wb") as f:
            shutil.copyfileobj(file.file, f)
            
        result = protect_pdf(in_p, temp_dir, password)
        
        if result:
            return handle_batch_response([result], background_tasks, temp_dir)
        raise HTTPException(400, "Échec de la protection du PDF")
    except Exception as e:
        cleanup(temp_dir)
        raise HTTPException(500, detail=str(e))
@app.post("/edit/sign")
async def sign_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    signature_base64: str = Form(...)
):
    temp_dir = tempfile.mkdtemp()
    try:
        # On sauvegarde le fichier pour pouvoir appliquer le filigrane après
        in_p = os.path.join(temp_dir, file.filename)
        file_bytes = await file.read()
        
        # Ton utilitaire doit renvoyer un buffer ou on le sauvegarde
        signed_buffer = process_pdf_signature(file_bytes, signature_base64)
        
        out_p = os.path.join(temp_dir, f"signed_{file.filename}")
        with open(out_p, "wb") as f:
            f.write(signed_buffer.getbuffer())
            
        # On passe par handle_batch_response pour avoir le filigrane et le cleanup
        return handle_batch_response([out_p], background_tasks, temp_dir)
    except Exception as e:
        cleanup(temp_dir)
        raise HTTPException(500, detail=str(e))                      
        # --- FRONTEND ---

if os.path.exists("assets"):
    app.mount("/assets", StaticFiles(directory="assets"), name="assets")

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Umbrella Engine Online</h1>"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)