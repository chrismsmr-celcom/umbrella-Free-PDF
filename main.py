import os
import io
import uuid
import shutil
import tempfile
import mimetypes
import time
import base64
from typing import List
from PIL import Image, ImageOps
from fastapi import APIRouter, Form, HTTPException

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
@app.get("/sw.js")
async def get_sw():
    # Assure-toi que le fichier sw.js est bien à la racine de ton projet
    return FileResponse("sw.js", media_type="application/javascript")
    
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
        # Nettoyage de la chaîne de pages (ex: "1,3,2" -> "1,3,2")
        pages = pages.strip()
        if not pages:
            raise HTTPException(400, "Aucun ordre de page reçu.")
            
        in_p = os.path.join(temp_dir, file.filename)
        with open(in_p, "wb") as f:
            shutil.copyfileobj(file.file, f)
            
        result = handle_reorder(in_p, pages, temp_dir)
        
        if result and os.path.exists(result):
            # IMPORTANT : On retourne le fichier directement avec FileResponse 
            # si tu ne veux pas passer par handle_batch_response qui peut zipper
            from fastapi.responses import FileResponse
            background_tasks.add_task(cleanup, temp_dir)
            return FileResponse(
                result, 
                media_type="application/pdf", 
                filename=f"umbrella_reordered_{int(time.time())}.pdf"
            )
        
        raise HTTPException(400, "Erreur lors du traitement PDF.")
    except Exception as e:
        if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
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
    # Récupérer l'extension originale
    ext = os.path.splitext(file.filename)[1].lower() or ".pdf"
    temp_in = f"temp_in_{uuid.uuid4().hex}{ext}"
    temp_out = f"edit_result_{uuid.uuid4().hex}.pdf"
    
    try:
        with open(temp_in, "wb") as f:
            shutil.copyfileobj(file.file, f)
            
        crop = {"x": x, "y": y, "w": w, "h": h} if x is not None else None
        
        from utils.edit import process_edit
        process_edit(temp_in, temp_out, rotation, crop)
        
        return FileResponse(temp_out, media_type="application/pdf", filename="umbrella_edited.pdf")
    except Exception as e:
        print(f"Erreur Edit: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # ICI : Il faut absolument 4 espaces devant le "if"
        if os.path.exists(temp_in): 
            os.remove(temp_in)
            
@app.post("/edit/save-final")
async def save_final_edit(
    background_tasks: BackgroundTasks,
    image_data: str = Form(...), 
    filename: str = Form(...)
):
    # 1. Création sécurisée du dossier temporaire
    temp_dir = tempfile.mkdtemp()
    # Nettoyage du nom de fichier pour éviter les problèmes d'extension double
    base_name = os.path.basename(filename).replace(".pdf", "")
    final_pdf_path = os.path.join(temp_dir, f"fixed_{base_name}.pdf")
    
    try:
        # 2. Décodage robuste du Base64
        # Le JS envoie souvent "data:image/png;base64,iVBOR..."
        try:
            if "," in image_data:
                header, imgstr = image_data.split(',')
            else:
                imgstr = image_data
            
            img_bytes = base64.b64decode(imgstr)
        except Exception as decode_err:
            print(f"Erreur décodage Base64: {decode_err}")
            raise HTTPException(status_code=400, detail="Données d'image corrompues.")

        temp_png_path = os.path.join(temp_dir, "canvas_overlay.png")
        with open(temp_png_path, "wb") as f:
            f.write(img_bytes)

        # 3. Traitement Pillow (Flattening)
        with Image.open(temp_png_path) as img:
            # Conversion en RGB indispensable pour le format PDF (qui ne gère pas la transparence PNG)
            # Cela "écrase" les calques et valide les biffures (redactions)
            rgb_img = img.convert("RGB")
            # 300 DPI pour une qualité professionnelle
            rgb_img.save(final_pdf_path, "PDF", resolution=300.0)

        # 4. Réponse avec tâche de fond pour supprimer le dossier complet
        return FileResponse(
            path=final_pdf_path,
            filename=f"umbrella_pro_{base_name}.pdf",
            media_type="application/pdf",
            background=background_tasks.add_task(cleanup, temp_dir)
        )

    except Exception as e:
        # Nettoyage immédiat en cas d'erreur
        cleanup(temp_dir)
        print(f"❌ Erreur Export Pro: {e}")
        # On renvoie l'erreur réelle pour le débuggage (à masquer en prod si besoin)
        raise HTTPException(status_code=500, detail=str(e))
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
    # Sécurité : on nettoie le nom de fichier
    safe_filename = os.path.basename(filename)
    # Assure-toi que STORAGE_DIR pointe bien au même endroit que lors de l'upload
    file_path = os.path.join(STORAGE_DIR, safe_filename)

    if not os.path.exists(file_path):
        print(f"❌ Fichier non trouvé sur le disque : {file_path}")
        raise HTTPException(status_code=404, detail="Fichier introuvable")

    # On ajoute un petit délai avant la suppression pour laisser le temps au stream de finir
    def delayed_remove(path):
        time.sleep(5) # Attendre 5 secondes après l'envoi
        if os.path.exists(path):
            os.remove(path)

    background_tasks.add_task(delayed_remove, file_path)
    
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
async def office_to_pdf_endpoint(
    background_tasks: BackgroundTasks, 
    file: UploadFile = File(...)
):
    # 1. Validation de l'extension pour éviter de lancer LibreOffice pour rien
    allowed_extensions = {'.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.odt', '.rtf'}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"Extension {ext} non supportée pour la conversion Office."
        )

    # 2. Création d'un répertoire temporaire unique (Isolation)
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Utilisation d'un nom de fichier sécurisé pour éviter les caractères spéciaux
        safe_filename = f"input{ext}" 
        in_p = os.path.join(temp_dir, safe_filename)
        
        # 3. Écriture par morceaux (Chunking) pour économiser la RAM sur les gros fichiers
        with open(in_p, "wb") as f:
            while chunk := await file.read(1024 * 1024): # 1MB chunks
                f.write(chunk)

        # 4. Conversion avec timeout et isolation (via ton utilitaire)
        # Note : Assure-toi que convert_to_pdf utilise l'argument -env:UserInstallation
        result = convert_to_pdf(in_p, temp_dir)
        
        if not result or not os.path.exists(result):
            raise Exception("Le moteur de conversion n'a pas généré de fichier.")

        # 5. Réponse via le handler générique avec nettoyage en arrière-plan
        return handle_batch_response([result], background_tasks, temp_dir)

    except Exception as e:
        # Nettoyage immédiat en cas d'échec avant la réponse
        background_tasks.add_task(cleanup, temp_dir)
        print(f"❌ PRO Error (Office2PDF): {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail="Erreur lors de la conversion du document Office."
        )

@app.post("/convert/pdf-to-word")
async def pdf_to_word_endpoint(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    temp_dir = tempfile.mkdtemp()
    try:
        in_p = os.path.join(temp_dir, file.filename)
        with open(in_p, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        # --- ÉTAPE 1 : DETECTION INTELLIGENTE ---
        # On vérifie si le PDF a besoin d'un OCR (s'il est vide de texte réel)
        from utils.ocr import needs_ocr, handle_ocr
        
        target_path = in_p
        if needs_ocr(in_p):
            print(f"🔍 Scan détecté pour {file.filename}, lancement de l'OCR avant conversion...")
            ocr_result = handle_ocr(in_p, temp_dir, language="fra")
            if ocr_result:
                target_path = ocr_result # On convertira le PDF "OCRisé"

        # --- ÉTAPE 2 : CONVERSION WORD ---
        # On utilise le PDF (original ou OCRisé) pour générer le .docx
        result = pdf_to_word(target_path, temp_dir)
        
        if result and os.path.exists(result):
            word_mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            filename_out = os.path.basename(result)
            
            background_tasks.add_task(cleanup, temp_dir)
            
            return FileResponse(
                path=result,
                filename=filename_out,
                media_type=word_mime
            )
            
        raise HTTPException(400, "La conversion Word a échoué.")
    except Exception as e:
        cleanup(temp_dir)
        print(f"🔥 Erreur PDF-to-Word: {e}")
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
            # On programme le nettoyage du dossier après la réponse
            background_tasks.add_task(cleanup, temp_dir)
            
            return FileResponse(
                path=result, 
                filename=f"{os.path.splitext(file.filename)[0]}.xlsx", 
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
        raise HTTPException(status_code=400, detail="Échec conversion Excel")
        
    except Exception as e:
        cleanup(temp_dir) # Nettoyage immédiat si erreur avant l'envoi
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/convert/pdf-to-pptx")
async def pdf_to_pptx_endpoint(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    temp_dir = tempfile.mkdtemp()
    try:
        in_p = os.path.join(temp_dir, file.filename)
        with open(in_p, "wb") as f:
            shutil.copyfileobj(file.file, f)
            
        result = pdf_to_pptx(in_p, temp_dir)
        
        if result and os.path.exists(result):
            background_tasks.add_task(cleanup, temp_dir)
            
            return FileResponse(
                path=result, 
                filename=f"{os.path.splitext(file.filename)[0]}.pptx", 
                media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation"
            )
        
        raise HTTPException(status_code=400, detail="La conversion PowerPoint a échoué.")
        
    except Exception as e:
        cleanup(temp_dir)
        raise HTTPException(status_code=500, detail=str(e))

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
            # Optionnel: on n'applique le watermark que si le fichier fait > 0 octets
            if os.path.getsize(result) > 0:
                # apply_watermark(result) # Désactive-le temporairement pour tester si c'est lui qui crash
                background_tasks.add_task(cleanup, temp_dir)
                return FileResponse(result, filename=f"searchable_{file.filename}", media_type="application/pdf")
        
        raise Exception("Le moteur OCR n'a pas pu traiter ce document.")
    except Exception as e:
        cleanup(temp_dir)
        print(f"🔥 Erreur OCR détaillée: {str(e)}")
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
    Garbage Collector optimisé pour Makem Group / 360PDF.
    Nettoie les sessions et fichiers de plus de 15 minutes.
    """
    now = time.time()
    expired_ids = []

    # 1. Identification des sessions périmées
    # On travaille sur une copie des clés pour être 100% safe
    for sid in list(scan_sessions.keys()):
        data = scan_sessions[sid]
        if (now - data.get("timestamp", 0)) > SCAN_EXPIRATION_TIME:
            file_path = data.get("path")
            
            # Suppression physique du fichier
            if file_path and os.path.exists(file_path):
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        print(f"🗑️ Fichier supprimé : {os.path.basename(file_path)}")
                except Exception as e:
                    print(f"⚠️ Erreur suppression fichier {sid}: {e}")
            
            expired_ids.append(sid)

    # 2. Nettoyage de la mémoire vive
    for sid in expired_ids:
        scan_sessions.pop(sid, None)

    if expired_ids:
        print(f"🧹 Umbrella GC : {len(expired_ids)} sessions nettoyées. Statut : OK.")

@app.post("/edit/unlock")
async def unlock_pdf_endpoint(
    background_tasks: BackgroundTasks, 
    file: UploadFile = File(...), 
    password: str = Form(...) 
):
    temp_dir = tempfile.mkdtemp()
    try:
        from utils.security import unlock_pdf # Assure-toi d'avoir cette fonction
        in_p = os.path.join(temp_dir, file.filename)
        with open(in_p, "wb") as f:
            shutil.copyfileobj(file.file, f)
            
        result = unlock_pdf(in_p, temp_dir, password)
        
        if result:
            return handle_batch_response([result], background_tasks, temp_dir)
        raise HTTPException(400, "Mot de passe incorrect ou erreur de déverrouillage")
    except Exception as e:
        cleanup(temp_dir)
        raise HTTPException(500, detail=str(e))

@app.post("/edit/translate")
async def translate_pdf_endpoint(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    target_lang: str = Form("en"),
    layout: str = Form("layout") # 'layout' (conserver) ou 'text' (uniquement texte)
):
    temp_dir = tempfile.mkdtemp()
    try:
        in_p = os.path.join(temp_dir, file.filename)
        with open(in_p, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # On importe la fonction qu'on a créée dans utils/translate.py
        from utils.translate import handle_translation
        
        # On lance la traduction (Open Source / Lingva)
        # On passe layout pour que handle_translation sache s'il doit garder le style
        result_pdf = await handle_translation(in_p, temp_dir, target_lang, layout)

        if result_pdf and os.path.exists(result_pdf):
            # On nettoie le dossier après l'envoi
            background_tasks.add_task(cleanup, temp_dir)
            
            return FileResponse(
                path=result_pdf,
                filename=f"translated_{target_lang}_{file.filename}",
                media_type="application/pdf"
            )
        
        raise Exception("La génération du PDF traduit a échoué.")

    except Exception as e:
        cleanup(temp_dir)
        print(f"❌ Erreur endpoint Traduction: {e}")
        raise HTTPException(500, detail=str(e))

@app.post("/edit/intelligence")
async def ai_pdf_analysis(
    file: UploadFile = File(...),
    task: str = Form("summary") # summary, keywords, or extract_data
):
    temp_dir = tempfile.mkdtemp()
    try:
        in_p = os.path.join(temp_dir, file.filename)
        with open(in_p, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # 1. Extraction du texte brut (nécessaire pour l'IA)
        from utils.ocr import get_text_content
        text_content = get_text_content(in_p)

        if not text_content.strip():
            raise Exception("Le document semble vide ou illisible.")

        # 2. Appel à un LLM (OpenAI GPT-4o ou Claude 3.5)
        from utils.ai import process_ai_task
        analysis_result = await process_ai_task(text_content, task)

        # On nettoie tout de suite car on renvoie du texte, pas un fichier
        cleanup(temp_dir)
        
        return {
            "status": "success",
            "task": task,
            "result": analysis_result
        }
    except Exception as e:
        cleanup(temp_dir)
        raise HTTPException(500, detail=f"Erreur IA : {str(e)}")

def cleanup(temp_path: str):
    if os.path.exists(temp_path):
        if os.path.isdir(temp_path):
            shutil.rmtree(temp_path)
        else:
            os.remove(temp_path)
            
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
