from flask import Flask, send_from_directory, request, jsonify
from threading import Thread
import textract
import os
import json
import requests

API_URL = "https://api-inference.huggingface.co/models/sentence-transformers/msmarco-distilbert-base-tas-b"
headers = {"Authorization": "Bearer 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"}

app = Flask(__name__)

def get_uploaded_files():
    upload_folder = app.config['UPLOAD_FOLDER']
    uploaded_files = []

    # Iterate over the files in the upload folder
    for filename in os.listdir(upload_folder):
        file_path = os.path.join(upload_folder, filename)
        if os.path.isfile(file_path):
            uploaded_files.append(filename)

    return uploaded_files

# Path for our main Svelte page
@app.route("/")
def base():
    return send_from_directory('client/public', 'index.html')

# Path for all the static files (compiled JS/CSS, etc.)
@app.route("/<path:path>")
def home(path):
    return send_from_directory('client/public', path)

def query(payload):
    response = requests.post(API_URL, headers=headers, json=payload)
    return response.json()

@app.route('/search', methods=['POST'])
def search():    
    data = request.json
    print(data['value'])
    output = query({
            "inputs": {
                "source_sentence": "happy dog",
                "sentences": [
                    "That is a happy dog",
                    "That is a very happy person",
                    "Today is a sunny day"
                ]
            }
        })
    return output

app.config['UPLOAD_FOLDER'] = 'uploads'

@app.route('/upload_file', methods=['POST'])
def upload_file():
    files = request.files.getlist('files[]')
    uploaded_files = []
    for file in files:
        filename = file.filename
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        uploaded_files.append(filename)
        text = textract.process("uploads/" + filename).decode('utf-8')
        print(text)

        name, extension = os.path.splitext(filename)

        file_path = "uploads/" + name + ".txt"

        # Open the file in write mode
        with open(file_path, "w") as file:
            # Write the contents of the variable to the file
            file.write(text)

        os.remove("uploads/" + filename)
        print("Done!")

    return jsonify({'Message': f'{len(uploaded_files)} Files uploaded successfullly'})

if __name__ == "__main__":
    app.run(debug=True, port=5002)

