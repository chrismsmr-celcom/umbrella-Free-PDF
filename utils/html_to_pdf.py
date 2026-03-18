import os
from weasyprint import HTML, CSS

def handle_html_to_pdf(input_data, output_dir):
    try:
        # 1. Sécurité : Vérifier que input_data n'est pas None ou vide
        if not input_data:
            print("❌ Erreur : input_data est vide")
            return None

        output_path = os.path.join(output_dir, "umbrella_converted_html.pdf")

        # Style CSS pour forcer le A4 sans marges
        styles = """
            @page {
                size: A4;
                margin: 0mm;
            }
            body { margin: 0; padding: 0; }
        """

        # 2. Gestion intelligente du contenu
        if isinstance(input_data, str) and os.path.exists(input_data):
            # C'est un FICHIER (ex: index.html)
            base_url = os.path.dirname(os.path.abspath(input_data))
            HTML(filename=input_data, base_url=base_url).write_pdf(
                output_path, 
                stylesheets=[CSS(string=styles)]
            )
        else:
            # C'est du HTML BRUT (string)
            # On force la conversion en string au cas où on recevrait des bytes
            html_string = str(input_data)
            HTML(string=html_string).write_pdf(
                output_path, 
                stylesheets=[CSS(string=styles)]
            )

        return output_path

    except Exception as e:
        print(f"❌ Erreur WeasyPrint HTML_TO_PDF : {e}")
        return None
