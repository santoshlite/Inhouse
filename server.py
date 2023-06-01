from flask import Flask, send_from_directory, request, jsonify
from transformers import AutoModelForQuestionAnswering, AutoTokenizer, pipeline
from sentence_transformers import SentenceTransformer, util
from threading import Thread
from pymongo import MongoClient
import textract
import os

import json


model = SentenceTransformer('sentence-transformers/msmarco-MiniLM-L6-cos-v5')

# Load model & tokenizer
deberta_model = AutoModelForQuestionAnswering.from_pretrained('navteca/deberta-v3-base-squad2')
deberta_tokenizer = AutoTokenizer.from_pretrained('navteca/deberta-v3-base-squad2')

nlp = pipeline('question-answering', model=deberta_model, tokenizer=deberta_tokenizer)


app = Flask(__name__)

@app.route("/get_uploaded_count")
def get_uploaded_count():
    upload_folder = app.config['UPLOAD_FOLDER']
    uploaded_files = []

    # Iterate over the files in the upload folder
    for filename in os.listdir(upload_folder):
        file_path = os.path.join(upload_folder, filename)
        if os.path.isfile(file_path) and filename.endswith('.txt'):
            uploaded_files.append(filename)
    return str(len(uploaded_files))


def get_uploaded_files():
    upload_folder = app.config['UPLOAD_FOLDER']
    uploaded_files = []

    # Iterate over the files in the upload folder
    for filename in os.listdir(upload_folder):
        file_path = os.path.join(upload_folder, filename)
        if os.path.isfile(file_path):
            uploaded_files.append(filename)

    return uploaded_file

def update_mongo_record(fileName, text):
    client = MongoClient(username="rootuser", password="rootpass") #Future todo => for deploy, add ip address in here

    db = client["myDatabase"]

    uploadFile = {
      "FileName": fileName,
      "Content": text
    }

    #Search for a collection called 'uploadFiles' under db database (create one if none is found)
    uploadFiles = db.uploadFiles

    uploadFiles.insert_one(uploadFile)

    client.close()

    pass

def clean_res(res):
    text = res['answer']

    # Remove leading and trailing whitespace
    text = text.strip()

    # Capitalize the first letter
    text = text.capitalize()

    # Add a period at the end if it's not already there
    if not text.endswith("."):
        text += "."

    return text


# Path for our main Svelte page
@app.route("/")
def base():
    return send_from_directory('client/public', 'index.html')

# Path for all the static files (compiled JS/CSS, etc.)
@app.route("/<path:path>")
def home(path):
    return send_from_directory('client/public', path)


@app.route('/search', methods=['POST'])
def search():    
    data = request.json
    query = data['value']
    directory = 'uploads'

    docs = []          

    for filename in os.listdir(directory):
            if filename.endswith('.txt'):  # Check if the file is a text file
                file_path = os.path.join(directory, filename)
                with open(file_path, 'r') as file:
                    content = file.read()
                    docs.append(content)
    
    if len(docs) == 0:
        return jsonify({'result': 'You need to upload files first!'})
    
    #Encode query and documents
    query_emb = model.encode(query)
    doc_emb = model.encode(docs)

    #Compute dot score between query and all document embeddings
    scores = util.dot_score(query_emb, doc_emb)[0].cpu().tolist()

    #Combine docs & scores
    doc_score_pairs = list(zip(docs, scores))

    #Sort by decreasing score
    doc_score_pairs = sorted(doc_score_pairs, key=lambda x: x[1], reverse=True)

    # Get the top 3 results or all results if there are fewer than 3
    top_3_results = [item[0] for item in doc_score_pairs[:3]]

    # Join the results into a single string
    joined_results = ' \n'.join(top_3_results)

    QA_input = {
        'question': query,
        'context': joined_results
    }
    
    print("waiting")
    out = nlp(QA_input)

    print("done")
    output = clean_res(out)
    
    response = {"result": output}
    print(response)
    return response

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

        name, extension = os.path.splitext(filename)

        file_path = "uploads/" + name + ".txt"

        # Open the file in write mode
        with open(file_path, "w") as file:
            # Write the contents of the variable to the file
            file.write(text)

        os.remove("uploads/" + filename)


        update_mongo_record(filename, text)

        print("Done!")


    return jsonify({'Message': f'{len(uploaded_files)} Files uploaded successfullly'})

if __name__ == "__main__":

    app.run(debug=True, port=5002)
