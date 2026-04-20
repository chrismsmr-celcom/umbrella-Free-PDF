import os
import hashlib
from pathlib import Path
from cryptography.fernet import Fernet
from pypdf import PdfReader, PdfWriter

def protect_pdf(input_path: str, output_dir: str, password: str) -> str:
    """
    Protège un PDF avec un mot de passe (chiffrement AES-128)
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"PDF introuvable: {input_path}")
    
    # Vérifier la force du mot de passe
    if len(password) < 4:
        raise ValueError("Le mot de passe doit faire au moins 4 caractères")
    
    output_path = os.path.join(output_dir, f"protected_{Path(input_path).name}")
    
    try:
        reader = PdfReader(input_path)
        writer = PdfWriter()
        
        # Copier toutes les pages
        for page in reader.pages:
            writer.add_page(page)
        
        # Ajouter la protection
        writer.encrypt(
            user_password=password,
            owner_password=None,  # Pas de mot de passe propriétaire
            permissions_flag=-44  # Permissions par défaut (impression, copie, etc.)
        )
        
        # Sauvegarder
        with open(output_path, 'wb') as f:
            writer.write(f)
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return output_path
        else:
            raise Exception("Fichier protégé non généré")
            
    except Exception as e:
        print(f"Erreur protection PDF: {e}")
        raise

def unlock_pdf(input_path: str, output_dir: str, password: str) -> str:
    """
    Déverrouille un PDF protégé par mot de passe
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"PDF introuvable: {input_path}")
    
    output_path = os.path.join(output_dir, f"unlocked_{Path(input_path).name}")
    
    try:
        reader = PdfReader(input_path)
        
        # Vérifier si le PDF est protégé
        if not reader.is_encrypted:
            raise ValueError("Ce PDF n'est pas protégé par mot de passe")
        
        # Tenter de déverrouiller
        if not reader.decrypt(password):
            raise ValueError("Mot de passe incorrect")
        
        writer = PdfWriter()
        
        # Copier toutes les pages
        for page in reader.pages:
            writer.add_page(page)
        
        # Sauvegarder sans mot de passe
        with open(output_path, 'wb') as f:
            writer.write(f)
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return output_path
        else:
            raise Exception("Fichier déverrouillé non généré")
            
    except Exception as e:
        print(f"Erreur déverrouillage PDF: {e}")
        raise

def add_watermark_to_pdf(input_path: str, output_path: str, watermark_text: str = "UMBRELLA PRO"):
    """
    Ajoute un filigrane textuel à un PDF
    """
    try:
        from pypdf import PdfReader, PdfWriter
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        import io
        
        # Créer le watermark
        packet = io.BytesIO()
        c = canvas.Canvas(packet, pagesize=letter)
        c.setFont("Helvetica", 30)
        c.setFillColorRGB(0.7, 0.7, 0.7, alpha=0.3)  # Gris semi-transparent
        c.saveState()
        c.translate(300, 400)  # Position
        c.rotate(45)  # Rotation
        c.drawString(0, 0, watermark_text)
        c.restoreState()
        c.save()
        
        packet.seek(0)
        watermark = PdfReader(packet)
        
        # Appliquer le watermark à chaque page
        reader = PdfReader(input_path)
        writer = PdfWriter()
        
        for page in reader.pages:
            page.merge_page(watermark.pages[0])
            writer.add_page(page)
        
        with open(output_path, 'wb') as f:
            writer.write(f)
        
        return output_path
        
    except Exception as e:
        print(f"Erreur ajout watermark: {e}")
        return input_path  # Retourne l'original si erreur