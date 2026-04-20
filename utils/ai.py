# utils/ai.py
import os
# import openai  # Commenté car non utilisé sur Render free
from typing import Dict, Any
import json

async def process_ai_task(text_content: str, task: str) -> Dict[str, Any]:
    """
    Traite une tâche IA (simulation sans OpenAI pour Render free)
    """
    # Version simplifiée sans API OpenAI
    if task == "summary":
        # Résumé basique (prendre les 500 premiers caractères)
        summary = text_content[:500] + "..." if len(text_content) > 500 else text_content
        return {
            "summary": summary,
            "note": "Version hors ligne - API OpenAI désactivée"
        }
    elif task == "extract":
        # Extraction basique
        words = text_content.split()
        return {
            "word_count": len(words),
            "char_count": len(text_content),
            "note": "Version hors ligne - API OpenAI désactivée"
        }
    elif task == "explain":
        return {
            "explanation": "Analyse hors ligne disponible. Activez l'API OpenAI pour plus de fonctionnalités.",
            "text_preview": text_content[:300]
        }
    else:
        return {
            "result": text_content[:500],
            "note": "Mode hors ligne - API OpenAI désactivée"
        }

# Version originale (à décommenter si vous installez openai)
"""
async def process_ai_task(text_content: str, task: str) -> Dict[str, Any]:
    try:
        openai.api_key = os.getenv("OPENAI_API_KEY")
        
        if task == "summary":
            prompt = f"Résume ce document en 3 phrases: {text_content[:3000]}"
        elif task == "extract":
            prompt = f"Extrait les informations clés de ce document: {text_content[:3000]}"
        elif task == "explain":
            prompt = f"Explique ce document simplement: {text_content[:3000]}"
        else:
            prompt = f"Analyse ce document: {text_content[:3000]}"
        
        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500
        )
        
        return {"result": response.choices[0].message.content}
    except Exception as e:
        return {"error": str(e), "result": "Erreur API"}
"""