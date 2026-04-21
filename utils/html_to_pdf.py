import os
from weasyprint import HTML, CSS

def handle_html_to_pdf(input_data, output_dir):
    try:
        if not input_data:
            print("Erreur: input_data est vide")
            return None

        output_path = os.path.join(output_dir, "umbrella_converted_html.pdf")

        styles = """
            @page {
                size: A4;
                margin: 0mm;
            }
            body { margin: 0; padding: 0; }
        """

        if isinstance(input_data, str) and os.path.exists(input_data):
            base_url = os.path.dirname(os.path.abspath(input_data))
            HTML(filename=input_data, base_url=base_url).write_pdf(
                output_path, 
                stylesheets=[CSS(string=styles)]
            )
        else:
            html_string = str(input_data)
            HTML(string=html_string).write_pdf(
                output_path, 
                stylesheets=[CSS(string=styles)]
            )

        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return output_path
        return None

    except Exception as e:
        print(f"Erreur WeasyPrint HTML_TO_PDF: {e}")
        return None