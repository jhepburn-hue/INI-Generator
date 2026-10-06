from flask import Flask, render_template, request, jsonify
from csv_parser import parse_csv_file, get_setting_value

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload():
    if "csv_file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files["csv_file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    content = file.read()
    rows = parse_csv_file(content)

if __name__ == "__main__":
    app.run(debug=True, port=5000)