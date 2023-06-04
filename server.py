from flask import Flask, send_from_directory, request, jsonify, redirect, render_template, session
from transformers import AutoModelForQuestionAnswering, AutoTokenizer, pipeline
from sentence_transformers import SentenceTransformer, util
import asyncio
import pymongo
from pymongo.mongo_client import MongoClient
import certifi
import secrets
import textract
import os

# Passage ranking model
model = SentenceTransformer('sentence-transformers/msmarco-MiniLM-L6-cos-v5')

app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = 'uploads'

# setting the mongodb client
uri = "mongodb+srv://inhouse:passwordinhouse@inhousedb.wglo6gd.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(uri, tlsCAFile=certifi.where())

# setting the 2 databases
db = client["userDocuments"]
db_history = client["userHistory"]

# setting the collection for authentification
token_email_collection = db["token_email_mapping"]


# setting up the url mapping table to use later on in redirecting user to appropriate sites
# this is a dictionary 
#   => keys are the url
#   => values are the directory names
URL_MAPPING = {
    '/': '/',
    '/auth': '/auth',
}

@app.route("/")
def base():
    return send_from_directory('client/public', 'frontpage.html')

@app.route("/app/<token>")
def svelte_app(token):
    email = get_email_from_token(token)
    if email:
        return send_from_directory('client/public', 'index.html')
    else:
        return redirect('/')
        
        # return "Invalid token or expired." => basically won't display this error message anymore
        # instead, will just redirect it to homescreen


# method returns the closest matching directory
def determine_closest_directory():
    requested_url = request.path
    closest_directory = None
    closest_distance = float('inf')

    for url_pattern, directory in URL_MAPPING.items():
        if url_pattern in requested_url:
            distance = len(requested_url) - len(url_pattern)
            if distance < closest_distance:
                closest_distance = distance
                closest_directory = directory

    print(closest_directory)
    return closest_directory


@app.errorhandler(404)
def page_not_found(e):
    closest_directory = determine_closest_directory()
    if closest_directory:
        return redirect(closest_directory)
    else:
        return render_template('404.html'), 404



@app.route("/auth")
def auth():
    return send_from_directory('client/public', 'auth.html')

@app.route("/<path:path>")
def home(path):
    return send_from_directory('client/public', path)

# generate a token for each new user
def generate_token():
    token = secrets.token_urlsafe(16)
    return token

# insert into out token_email_mapping collection a new user (token, email, password)
def associate_email_with_token(token, email, password):
    token_email_collection.insert_one({"token": token, "email": email, "password": password})

# retrieve the email from the token in our token_email_mapping collection
def get_email_from_token(token):
    result = token_email_collection.find_one({"token": token})
    if result:
        return result["email"]
    else:
        return None
    
# retrieve the token from the email in our token_email_mapping collection
def get_token_from_email(email):
    document = token_email_collection.find_one({'email': email})
    if document:
        return document["token"]
    return None

# retrieve the password from the email in our token_email_mapping collection
def get_password_from_email(email):
    document = token_email_collection.find_one({'email': email})
    if document:
        return document["password"]
    return None

# authenticate the user or create a new user
@app.route("/login", methods=['POST'])
def login():

    # retrieve the email and password from the form
    email = request.form['email']
    password = request.form['password']

    # check if the user already exists
    existing_token = get_token_from_email(email)
    existing_password = get_password_from_email(email)

    # if the user exists and the password is correct, redirect to the app
    if existing_token and existing_password == password:
        token = existing_token
        return redirect(f"/app/{token}")
    
    # if the user exists but the password is incorrect, redirect to the auth page
    elif existing_token and existing_password != password:
        return redirect("/auth?error=wrong_password")

    # if the user does not exist, create a new user and token, store its password
    else:
        token = generate_token()
        associate_email_with_token(token, email, password)

    return redirect(f"/app/{token}")

# get the number of files uploaded by the user -> to display under search bar
@app.route("/app/get_uploaded_count/<token>")
def get_uploaded_count(token):
    email = get_email_from_token(token)

    if email is None:
        return "Invalid token"
    
    collection = db[email]
    uploaded_files = collection.count_documents({})
    return str(uploaded_files)


# add file to the database
def update_mongo_record(collection, fileName, text):
    uploadFile = {
        "FileName": fileName,
        "Content": text
    }
    collection.insert_one(uploadFile)
    
    pass

# Append the query-response into the history database
def record_history(collection, query, response):
    
    pastRecord = {
        "Query":  query,
        "Response": response
    }
    
    collection.insert_one(pastRecord)

    pass

# get the list of all queries from the user from the history database
@app.route("/app/get_history_list/<token>")
def get_history_list(token):
    email = get_email_from_token(token)

    if email is None:
        return jsonify({"error": "Invalid token"})
    
    history_collection = db_history[email]
    history_documents = history_collection.find({}).sort("_id", pymongo.DESCENDING)

    query_list = [doc["Query"] for doc in history_documents]

    return jsonify({"queries": query_list})


# where the magic happens
@app.route('/app/search/<token>', methods=['POST'])
def search(token):    

    # Get the email associated with the token
    email = get_email_from_token(token)

    if email is None:
        return jsonify({'result': 'Could not find the user.'})

    data = request.json
    query = data['value'] 

    collection = db_history[email]

    response = "Result of the search here"

    record_history(collection, query, response)

    return {"result": response}


async def upload_single_file(file, collection):

        print("===================================== STEP 1: ENTERED UPLOAD SINGLE FILE! ===================================")
        filename = file.filename
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        text = textract.process("uploads/" + filename).decode('utf-8')

        name, extension = os.path.splitext(filename)

        file_path = "uploads/" + name + ".txt"

        # Open the file in write mode
        with open(file_path, "w") as file:
            # Write the contents of the variable to the file
            file.write(text)

        os.remove("uploads/" + filename)

        update_mongo_record(collection, filename, text)
        print("===================================== STEP 2: UPDATED MONGO RECORD! ===================================")


async def upload_multiple_file(collection):
    files = request.files.getlist('files[]')

    for file in files:
        asyncio.ensure_future(upload_single_file(file, collection))
    
    print("===================================== GENERAL STEP 3: UPLOADED ALL FILE FROM FILES! ===================================")

@app.route('/app/upload_file/<token>', methods=['POST'])
def upload_file(token):

    # Get the email associated with the token
    email = get_email_from_token(token)

    if email is None:
        return jsonify({'Message': 'Invalid token'})

    # Get the collection based on the email
    collection = db[email]

    print("===================================== STEP 4: ENTERED UPLOAD_FILE ===================================")
    files = request.files.getlist('files[]')
    uploaded_files = []
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(upload_multiple_file(collection))
    loop.close()

    for file in files:
        filename = file.filename
        uploaded_files.append(filename)

    print("===================================== STEP 5: FINAL STAGE ===================================")
    return jsonify({'Message': f'{len(uploaded_files)} Files uploaded successfullly'})


if __name__ == "__main__":
    app.run(debug=True, port=5002)
