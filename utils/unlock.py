from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
import pikepdf
import io

# On définit le prefix /edit car ton front-end appelle /edit/unlock
router = APIRouter(prefix="/edit", tags=["Security"])

@router.post("/unlock")
async def unlock_pdf(
    file: UploadFile = File(...),
    password: str = Form(...)
):
    """
    Supprime la protection par mot de passe d'un fichier PDF.
    Utilise pikepdf pour reconstruire le PDF sans restrictions.
    """
    try:
        # Lecture du fichier envoyé
        content = await file.read()
        
        # Tentative d'ouverture avec le mot de passe fourni
        try:
            # pikepdf.open charge le PDF en mémoire
            with pikepdf.open(io.BytesIO(content), password=password) as pdf:
                # Création d'un buffer mémoire pour le nouveau fichier
                out_buffer = io.BytesIO()
                
                # Sauvegarde du PDF "propre" (sans mot de passe) dans le buffer
                pdf.save(out_buffer)
                out_buffer.seek(0)
                
                # On retourne le fichier directement au navigateur
                return StreamingResponse(
                    out_buffer,
                    media_type="application/pdf",
                    headers={
                        "Content-Disposition": f"attachment; filename=unlocked_{file.filename}"
                    }
                )
        except pikepdf.PasswordError:
            # Cas où le mot de passe est faux
            raise HTTPException(status_code=401, detail="Le mot de passe fourni est incorrect.")
            
    except Exception as e:
        # Autres erreurs (fichier corrompu, format invalide, etc.)
        raise HTTPException(status_code=500, detail=f"Erreur système : {str(e)}")