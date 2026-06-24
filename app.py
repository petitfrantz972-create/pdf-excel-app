from flask import Flask, render_template_string, request, send_file
import pdfplumber
import pandas as pd
import re
import os

app = Flask(__name__)


def extract_data(pdf_path):
    data = []
    current_dci = None

    with pdfplumber.open(pdf_path) as pdf:
        text = ""
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text += t + "
"

    marche = re.search(r"Code Marché\s+(\d+)", text)
    marche = marche.group(1) if marche else None

    dates = re.search(r"Du (\d{2}/\d{2}/\d{4}) au (\d{2}/\d{2}/\d{4})", text)
    d_start, d_end = (dates.groups() if dates else (None, None))

    lines = text.split("
")

    for line in lines:
        line = line.strip()

        if re.match(r"^[A-Z\s\(\)\-]+$", line) and len(line) > 5:
            current_dci = line

        match = re.search(r"(.+?)\s+(\d+/\d+)\s+\d+\s+([\d\s]+)\s+([\d\.]+).*?([\d\.]+)\s+F-\d+", line)

        if match:
            data.append({
                "DCI": current_dci,
                "Marché": marche,
                "Début Marché": d_start,
                "Fin Marché": d_end,
                "Dénomination": match.group(1),
                "Condt": match.group(2),
                "Quantité": match.group(3).replace(" ", ""),
                "Tarif HT": match.group(4),
                "PU TTC": match.group(5)
            })

    return pd.DataFrame(data)

HTML = """
<!doctype html>
<html>
<head>
    <title>PDF → Excel PRO</title>
    <style>
        body { font-family: Arial; text-align:center; padding:20px; }
        table { border-collapse: collapse; margin:auto; }
        th, td { border:1px solid #ccc; padding:5px; }
        th { background:#eee; }
    </style>
</head>
<body>

<h2>Convertisseur PDF → Excel</h2>

<form method="post" enctype="multipart/form-data">
    <input type="file" name="files" multiple>
    <br><br>
    <button type="submit">Convertir</button>
</form>

{% if tables %}
    <h3>Aperçu des données</h3>
    {{ tables|safe }}
    <br><br>
    <a href="/download">Télécharger Excel</a>
{% endif %}

</body>
</html>
"""

last_file = "result.xlsx"

@app.route("/", methods=["GET", "POST"])
def index():
    global last_file
    table_html = None

    if request.method == "POST":
        files = request.files.getlist("files")
        all_df = pd.DataFrame()

        for f in files:
            path = f.filename
            f.save(path)
            df = extract_data(path)
            all_df = pd.concat([all_df, df])
            os.remove(path)

        last_file = "result.xlsx"
        all_df.to_excel(last_file, index=False)
        table_html = all_df.head(50).to_html()

    return render_template_string(HTML, tables=table_html)

@app.route("/download")
def download():
    return send_file(last_file, as_attachment=True)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
