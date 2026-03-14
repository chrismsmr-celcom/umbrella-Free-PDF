import os
from weasyprint import HTML, CSS

def handle_html_to_pdf(input_data, output_dir):
    """
    Convertit du contenu HTML ou un fichier HTML en PDF via WeasyPrint.
    Plus besoin de configuration de binaire externe (wkhtmltopdf).
    """
    try:
        output_path = os.path.join(output_dir, "umbrella_converted_html.pdf")

        # Configuration des marges et du format via CSS (plus propre)
        base_url = os.path.dirname(input_data) if os.path.exists(input_data) else None
        
        # Styles par défaut pour simuler tes anciennes options
        stylesheets = [CSS(string="@page { size: A4; margin: 0mm; }")]

        if isinstance(input_data, str) and os.path.exists(input_data):
            # Conversion depuis un fichier local
            HTML(filename=input_data, base_url=base_url).write_pdf(
                output_path, 
                stylesheets=stylesheets
            )
        else:
            # Conversion depuis une string HTML brute
            HTML(string=input_data).write_pdf(
                output_path, 
                stylesheets=stylesheets
            )

        if os.path.exists(output_path):
            return output_path
        return None

    except Exception as e:
        print(f"❌ Erreur critique HTML_TO_PDF (WeasyPrint) : {e}")
        return None
