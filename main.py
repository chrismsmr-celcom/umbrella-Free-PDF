import os
import io
import uuid
import shutil
import tempfile
import mimetypes
import time
from typing import List

# FastAPI & Responses
from fastapi import FastAPI, UploadFile, File, HTTPException, Form, BackgroundTasks, Request
from fastapi.responses import FileResponse, StreamingResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Traitement d'images
from PIL import Image

# --- UTILS UMBRELLA ---
from utils.core import cleanup, create_zip_on_disk
from utils.security import protect_pdf
from utils.sign_utils import process_pdf_signature

# Conversion & Office
from utils.office import (
    convert_to_pdf, pdf_to_word, pdf_to_excel, 
    pdf_to_pptx, pdf_to_pdfa
)
from utils.html_to_pdf import handle_html_to_pdf

# Manipulation PDF
from utils.images import images_to_pdf, pdf_to_images
from utils.organize import handle_extract, handle_remove, handle_reorder
from utils.merge import handle_merge
from utils.split import handle_split
from utils.scan import handle_scan_effect
from utils.watermark import apply_watermark
from utils.repair import handle_repair
from utils.ocr import handle_ocr
from utils.compress import handle_compress

app = FastAPI(title="Umbrella PDF Engine PRO")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONFIGURATION ---
scan_sessions = {}
STORAGE_DIR = os.path.join(tempfile.gettempdir(), "umbrella_scans")
os.makedirs(STORAGE_DIR, exist_ok=True)
# Durée de vie d'un scan (ex: 15 minutes)
SCAN_EXPIRATION_TIME = 15 * 60

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
        if not pages or pages.strip() == "":
            raise HTTPException(400, "L'ordre des pages est invalide.")
            
        in_p = os.path.join(temp_dir, file.filename)
        with open(in_p, "wb") as f:
            shutil.copyfileobj(file.file, f)
            
        result = handle_reorder(in_p, pages, temp_dir)
        if result:
            # On utilise handle_batch_response pour tout uniformiser (watermark + cleanup)
            return handle_batch_response([result], background_tasks, temp_dir)
        
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

@app.post("/edit/process")
async def edit_document(
    file: UploadFile = File(...),
    rotation: int = Form(0),
    x: float = Form(None),
    y: float = Form(None),
    w: float = Form(None),
    h: float = Form(None)
):
    temp_in = f"temp_in_{uuid.uuid4().hex}"
    temp_out = f"edit_result_{uuid.uuid4().hex}.pdf"
    
    with open(temp_in, "wb") as f:
        shutil.copyfileobj(file.file, f)
        
    crop = {"x": x, "y": y, "w": w, "h": h} if x is not None else None
    
    try:
        from utils.edit import process_edit
        process_edit(temp_in, temp_out, rotation, crop)
        return FileResponse(temp_out, media_type="application/pdf", filename="umbrella_edited.pdf")
    finally:
        if os.path.exists(temp_in): os.remove(temp_in)
# --- SCAN MOBILE ---

@app.get("/scan/generate-session")
async def generate_scan_session(request: Request, background_tasks: BackgroundTasks):
    """
    Prépare une nouvelle session de scan et déclenche le nettoyage des anciennes.
    """
    background_tasks.add_task(cleanup_expired_scans)
    
    session_id = uuid.uuid4().hex[:8]
    # Initialisation de la session avec le timestamp actuel
    scan_sessions[session_id] = {"path": None, "timestamp": time.time()}
    
    # Construction de l'URL absolue pour le QR Code / Mobile
    host_url = str(request.base_url).rstrip('/')
    return {
        "session_id": session_id, 
        "url": f"{host_url}/mobile-scan?s={session_id}"
    }

@app.get("/mobile-scan", response_class=HTMLResponse)
async def serve_mobile_scan_page(request: Request, s: str = None):
    """
    Sert l'interface de capture mobile.
    """
    if not s or (s not in scan_sessions and s != "test"):
         raise HTTPException(status_code=403, detail="Session invalide ou expirée")

    page_path = "mobile_scan.html"
    if os.path.exists(page_path):
        with open(page_path, "r", encoding="utf-8") as f:
            return f.read()
    return HTMLResponse("<h1>Erreur : Interface mobile introuvable</h1>", status_code=404)

@app.post("/scan/upload-mobile/{session_id}")
async def upload_from_mobile(
    session_id: str, 
    file: UploadFile = File(...), 
    mode: str = Form("color")
):
    """
    Réceptionne l'image du mobile, applique l'effet scan et génère le PDF.
    """
    if session_id not in scan_sessions:
        raise HTTPException(status_code=404, detail="Session expirée")

    try:
        # Sécurisation du fichier temporaire
        file_id = uuid.uuid4().hex[:6]
        ext = os.path.splitext(file.filename)[1] or ".jpg"
        temp_img_path = os.path.join(STORAGE_DIR, f"raw_{file_id}{ext}")

        # Sauvegarde sur disque pour éviter de saturer la RAM
        with open(temp_img_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Appel du traitement d'image (ton utilitaire)
        from utils.scan import handle_scan_effect
        scanned_pdf = handle_scan_effect(temp_img_path, STORAGE_DIR, mode=mode)

        if scanned_pdf and os.path.exists(scanned_pdf):
            # Mise à jour de la session avec le chemin du PDF final
            scan_sessions[session_id] = {
                "path": scanned_pdf,
                "timestamp": time.time() # Refresh du timer
            }
            # Nettoyage immédiat de l'image brute (raw)
            if os.path.exists(temp_img_path): os.remove(temp_img_path)
            
            return {"status": "success", "message": "Document prêt"}
        
        raise Exception("Le traitement de l'image a échoué.")

    except Exception as e:
        print(f"❌ Erreur Scan Mobile: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne de traitement")

@app.get("/scan/check-session/{session_id}")
async def check_session(session_id: str):
    """
    Le PC interroge cette route pour savoir si le mobile a fini l'upload.
    """
    session_data = scan_sessions.get(session_id)
    if session_data and session_data["path"] and os.path.exists(session_data["path"]):
        return {
            "ready": True, 
            "filename": os.path.basename(session_data["path"])
        }
    return {"ready": False}

@app.get("/scan/get-result/{filename}")
async def get_scan_result(filename: str, background_tasks: BackgroundTasks):
    """
    Téléchargement final du PDF et suppression immédiate après envoi.
    """
    # Protection anti-injection de chemin
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(STORAGE_DIR, safe_filename)

    if os.path.exists(file_path):
        # Suppression du fichier dès que le téléchargement est terminé
        background_tasks.add_task(os.remove, file_path)
        return FileResponse(
            file_path, 
            media_type="application/pdf", 
            filename="umbrella_scan.pdf"
        )

    raise HTTPException(status_code=404, detail="Fichier introuvable")

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
        if file: # Vérifie si un fichier a été uploadé
            in_p = os.path.join(temp_dir, file.filename)
            with open(in_p, "wb") as f:
                shutil.copyfileobj(file.file, f)
            input_data = in_p
        elif html_content:
            input_data = html_content
        
        if not input_data:
            raise HTTPException(400, "Aucun contenu HTML ou fichier fourni.")

        result = handle_html_to_pdf(input_data, temp_dir)
        return handle_batch_response([result], background_tasks, temp_dir)
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
        in_p = os.path.join(temp_dir, file.filename)
        # On sauvegarde sur disque d'abord pour préserver la RAM
        with open(in_p, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # On lit le fichier seulement au moment du traitement
        with open(in_p, "rb") as f:
            file_bytes = f.read()
        
        signed_buffer = process_pdf_signature(file_bytes, signature_base64)
        
        out_p = os.path.join(temp_dir, f"signed_{file.filename}")
        with open(out_p, "wb") as f:
            f.write(signed_buffer.getbuffer())
            
        return handle_batch_response([out_p], background_tasks, temp_dir)
    except Exception as e:
        background_tasks.add_task(cleanup, temp_dir)
        raise HTTPException(500, detail=str(e))

def cleanup_expired_scans():
    """
    Garbage Collector : Supprime les fichiers et les sessions expirés.
    Empêche la saturation du stockage éphémère de Render.
    """
    now = time.time()
    expired_ids = []

    for sid, data in scan_sessions.items():
        if (now - data["timestamp"]) > SCAN_EXPIRATION_TIME:
            # Suppression du fichier physique s'il existe
            if data["path"] and os.path.exists(data["path"]):
                try:
                    os.remove(data["path"])
                except Exception as e:
                    print(f"⚠️ Erreur nettoyage fichier session {sid}: {e}")
            expired_ids.append(sid)

    for sid in expired_ids:
        del scan_sessions[sid]
    if expired_ids:
        print(f"🧹 Nettoyage : {len(expired_ids)} sessions expirées supprimées.")
        
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
