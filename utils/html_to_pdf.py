import os
from weasyprint import HTML, CSS

def handle_html_to_pdf(input_data, output_dir):
    try:
        output_path = os.path.join(output_dir, "umbrella_converted_html.pdf")

        # Configuration du style pour forcer le format A4 et marges à zéro comme dans tes options précédentes
        base_url = os.path.dirname(input_data) if os.path.exists(input_data) else None
        
        # Style CSS pour simuler tes anciennes options
        styles = """
            @page {
                size: A4;
                margin: 0mm;
            }
        """

        # Si input_data est un chemin de fichier existant
        if isinstance(input_data, str) and os.path.exists(input_data):
            HTML(filename=input_data, base_url=base_url).write_pdf(
                output_path, 
                stylesheets=[CSS(string=styles)]
            )
        else:
            # Si c'est du contenu HTML brut (string)
            HTML(string=input_data).write_pdf(
                output_path, 
                stylesheets=[CSS(string=styles)]
            )

        return output_path

    except Exception as e:
        print(f"❌ Erreur WeasyPrint HTML_TO_PDF : {e}")
        return None
