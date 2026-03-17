import os
import openai # pip install openai
from utils.ocr import handle_ocr

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = openai.OpenAI(api_key=OPENAI_API_KEY)

async def process_ai_task(text_content, task):
    """
    Envoie le contenu du PDF à un LLM avec un prompt spécifique.
    """
    prompts = {
        "summary": "Fais un résumé concis et professionnel du document suivant en français :",
        "keywords": "Extrais les 10 mots-clés les plus importants de ce document :",
        "extract_data": "Extrais les dates, montants et noms d'entreprises sous forme de liste à puces :"
    }

    selected_prompt = prompts.get(task, prompts["summary"])

    try:
        # On limite le texte pour ne pas dépasser les limites de l'API (ex: 4000 mots)
        truncated_text = text_content[:15000] 

        response = client.chat.completions.create(
            model="gpt-4o-mini", # Modèle rapide et économique
            messages=[
                {"role": "system", "content": "Tu es Umbrella AI, un expert en analyse de documents PDF."},
                {"role": "user", "content": f"{selected_prompt}\n\n{truncated_text}"}
            ],
            temperature=0.3 # Plus bas pour être plus précis
        )

        return response.choices[0].message.content
    except Exception as e:
        return f"Erreur lors du traitement IA : {str(e)}"
