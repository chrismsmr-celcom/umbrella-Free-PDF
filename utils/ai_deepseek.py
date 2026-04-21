import os
import json
from typing import Dict, Any
import httpx

# Configuration DeepSeek
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

async def process_ai_task_deepseek(text_content: str, task: str) -> Dict[str, Any]:
    """
    Traite une tâche IA avec DeepSeek API
    """
    if not DEEPSEEK_API_KEY:
        return {
            "error": "Clé API DeepSeek non configurée",
            "note": "Ajoutez DEEPSEEK_API_KEY dans les variables d'environnement"
        }
    
    # Construction du prompt selon la tâche
    prompts = {
        "summary": f"Résume ce document de façon concise en 3 à 5 phrases:\n\n{text_content[:4000]}",
        "extract": f"Extrait les informations clés de ce document (dates, noms, chiffres, lieux):\n\n{text_content[:4000]}",
        "explain": f"Explique ce document simplement comme si je n'avais pas de connaissances techniques:\n\n{text_content[:4000]}",
        "keywords": f"Extrait les 10 mots-clés les plus importants de ce document:\n\n{text_content[:4000]}",
        "sentiment": f"Analyse le ton et le sentiment de ce document:\n\n{text_content[:4000]}"
    }
    
    prompt = prompts.get(task, f"Analyse ce document: {text_content[:4000]}")
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                DEEPSEEK_API_URL,
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": "Vous êtes un assistant expert en analyse de documents PDF. Répondez en français de manière claire et professionnelle."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 1000
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                result = data["choices"][0]["message"]["content"]
                return {
                    "status": "success",
                    "task": task,
                    "result": result,
                    "provider": "DeepSeek"
                }
            else:
                return {
                    "error": f"DeepSeek API error: {response.status_code}",
                    "detail": response.text
                }
                
    except Exception as e:
        return {
            "error": f"Erreur DeepSeek: {str(e)}"
        }

async def process_ai_task_fallback(text_content: str, task: str) -> Dict[str, Any]:
    """
    Version de fallback sans API (gratuite, hors ligne)
    """
    if task == "summary":
        summary = text_content[:500] + "..." if len(text_content) > 500 else text_content
        return {
            "status": "success",
            "task": task,
            "result": summary,
            "word_count": len(text_content.split()),
            "note": "Version hors ligne - Connectez DeepSeek pour plus de précision"
        }
    elif task == "extract":
        import re
        mots = re.findall(r'\b[A-Z][a-z]+\b', text_content)
        return {
            "status": "success",
            "task": task,
            "keywords": list(set(mots))[:15],
            "char_count": len(text_content),
            "note": "Version hors ligne - Connectez DeepSeek pour plus de précision"
        }
    else:
        return {
            "status": "success",
            "task": task,
            "result": text_content[:500],
            "note": "Version hors ligne - Connectez DeepSeek pour plus de fonctionnalités"
        }

async def process_ai_task(text_content: str, task: str) -> Dict[str, Any]:
    """
    Point d'entrée principal - essaie DeepSeek d'abord, puis fallback
    """
    # Essayer DeepSeek d'abord
    result = await process_ai_task_deepseek(text_content, task)
    
    if "error" not in result:
        return result
    
    # Fallback hors ligne
    print(f"DeepSeek indisponible, utilisation du mode hors ligne: {result.get('error')}")
    return await process_ai_task_fallback(text_content, task)