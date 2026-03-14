import pdfkit
import os
import platform

def handle_html_to_pdf(input_data, output_dir):
    try:
        if platform.system() == "Windows":
            path_wkhtmltopdf = r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
            config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)
        else:
            config = pdfkit.configuration()

        output_path = os.path.join(output_dir, "umbrella_converted_html.pdf")

        options = {
            'page-size': 'A4',
            'encoding': "UTF-8",
            'margin-top': '0mm',
            'margin-right': '0mm',
            'margin-bottom': '0mm',
            'margin-left': '0mm',
            'enable-local-file-access': None,
            'quiet': '', 
            'load-error-handling': 'ignore',         # <--- Crucial
            'load-media-error-handling': 'ignore',   # <--- Crucial
            'disable-smart-shrinking': None
        }

        # Si input_data est un chemin de fichier existant
        if isinstance(input_data, str) and os.path.exists(input_data):
            pdfkit.from_file(input_data, output_path, configuration=config, options=options)
        else:
            # Si c'est du contenu HTML brut (string)
            pdfkit.from_string(input_data, output_path, configuration=config, options=options)

        return output_path

    except Exception as e:
        print(f"❌ Erreur critique HTML_TO_PDF : {e}")
        return None