from __future__ import print_function
from flask import Flask, send_from_directory, request, jsonify, redirect, render_template, session
from g_drive_service import GoogleDriveService
import io
import gdown

import google.auth
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from sentence_transformers import SentenceTransformer, util
import asyncio
import pymongo
from pymongo.mongo_client import MongoClient
import certifi
import secrets
import textract
import heapq
import openai
import os
import re

# OpenAI API key
openai.api_key = os.getenv('OPENAI_API_KEY')

# MongoDB password
db_password = os.getenv('DB_PASSWORD')

# Passage ranking model
model = SentenceTransformer('sentence-transformers/msmarco-MiniLM-L6-cos-v5')

app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = 'uploads'

# setting the mongodb client
uri = f"mongodb+srv://inhouse:{db_password}@inhousedb.wglo6gd.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(uri, tlsCAFile=certifi.where())



# Build google drive service
service=GoogleDriveService().build()

# setting up the url mapping table to use later on in redirecting user to appropriate sites
# this is a dictionary 
#   => keys are the url
#   => values are the directory names
URL_MAPPING = {
    '/': '/',
    '/auth': '/auth',
}

# setting the 2 databases
db = client["userDocuments"]
db_history = client["userHistory"]

# setting the collection for authentification
token_email_collection = db["token_email_mapping"]

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
def update_mongo_record(collection, fileName, text, blocks):
    uploadFile = {
        "FileName": fileName,
        "Content": text,
        "Blocks": blocks, 
    }
    collection.insert_one(uploadFile)
    
    pass

def record_history(collection, query, response):
    # Check if the query already exists in the collection
    existing_query = collection.find_one({'Query': query})

    if existing_query:
        # Increment the count by 1 and append it to the query
        count = existing_query.get('Count', 1) + 1
        query_with_count = f"{query} #{count}"

        # Update the existing query with the updated count and query
        collection.update_one(
            {'Query': query},
            {'$set': {'Query': query, 'Count': count, 'Response': response}}
        )

        # Add the query as a new entry with count as 1
        new_record = {
            'Query': query_with_count,
            'Count': 1,
            'Response': response
        }
        
        collection.insert_one(new_record)
    else:

        # Add the query as a new entry with count as 1
        new_record = {
            'Query': query,
            'Count': 1,
            'Response': response
        }
        collection.insert_one(new_record)

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


@app.route("/app/get_response_from_query/<token>", methods=['POST'])
def get_response_from_query(token):
    responseValue = "Loading response..."
    data = request.json
    query = data['value']

    # Get the email associated with the token
    email = get_email_from_token(token)
    history_collection = db_history[email]

    if email is None:
        return jsonify({'response': 'Invalid token'})
    
    # Find the most recent document in the collection that matches the query
    result = history_collection.find_one({'Query': query})

    if result:
        response = result['Response']
        return jsonify({'response': response})
    else:
        return jsonify({'response': 'Response not found'})

# transform files to blocks
def file_to_blocks(content, k, docname):
    # Split the content into sentences
    sentences = re.split(r'(?<=\. )|\n', content)
    sentences = [element.strip() for element in sentences if element]
    
    blocks = []
    current_block = ""
    for sentence in sentences:
        if len(current_block) + len(sentence) <= k:
            current_block += sentence + " "
        else:
            blocks.append(docname + " - " + current_block.strip())
            current_block = sentence + " "

    if current_block:
        blocks.append(docname + " - " + current_block.strip())

    return blocks


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

        # Get the blocks from the file
        blocks = file_to_blocks(text, 300, filename)

        os.remove("uploads/" + filename)

        update_mongo_record(collection, filename, text, blocks)

        print("===================================== STEP 2: UPDATED MONGO RECORD! ===================================")


async def upload_multiple_file(collection):
    files = request.files.getlist('files[]')

    for file in files:
        asyncio.ensure_future(upload_single_file(file, collection))
    
    print("===================================== GENERAL STEP 3: UPLOADED ALL FILE FROM FILES! ===================================")







# This function gets all the files underneath a certain folder containing a given ID 
@app.get('/files-in-folder/<folder_id>/')
def get_files_in_folder(folder_id, collection):
    
    selected_field="files(id, name, webViewLink)"
    query=f" '{folder_id}' in parents "
    
    list_of_files = service.files().list(
        q=query,
        fields=selected_field
    ).execute()

    name_id_dict = {}

    # Loop through list of dictionaries and retrieve name and id of each file
    for i in range(len(list_of_files["files"])):

        print(i)
        name = list_of_files["files"][i]["name"]
        id = list_of_files["files"][i]["id"]

        # Construct new dictionary
        name_id_dict[name] = id


    return name_id_dict


# This function first download the file, then upload it to the mongo database
async def upload_single_google_file(filename, id, collection):

    gdown.download("https://drive.google.com/uc?id="+id, filename, quiet=False, fuzzy=True)
    
    ext = os.path.splitext(filename)[1]

    if ext == "":
        text = textract.process(filename, extension='docx').decode('utf-8')
    else:
        text = textract.process(filename).decode('utf-8')

    with open(filename, "w") as file:
            # Write the contents of the variable to the file
            file.write(text)
    
    # Get the blocks from the file
    blocks = file_to_blocks(text, 300, filename)

    os.remove(filename)

    update_mongo_record(collection, filename, text, blocks)


async def upload_multiple_google_file(folder_id, collection):

    name_id_dictionary = get_files_in_folder(folder_id, collection)

    for key, value in name_id_dictionary.items():
        asyncio.ensure_future(upload_single_google_file(key, value, collection))
    


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


@app.route('/app/upload_google_file/<token>/<folder_id>', methods=['POST'])
def upload_google_file(token, folder_id):
# Get the email associated with the token
    email = get_email_from_token(token)

    if email is None:
        return jsonify({'Message': 'Invalid token'})

    # Get the collection based on the email
    collection = db[email]

    # NEEDS TO BE IMPLEMENTED!!!! => FOLDER - ID RETRIEVED!!!!
    # folder_id = "1sckveKrkTZ6AlBBrufAsBAJUQMr_eZqM"

    # upload_multiple_google_file(folder_id, collection)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(upload_multiple_google_file(folder_id,collection))
    loop.close()


    print("===================================== STEP 5: FINAL STAGE ===================================")
    return jsonify({'Message': f'Google Files uploaded successfullly'})

######################################
#####################################
#####################################


def construct_prompt(query, top_blocks, history):

    prompt = []

    system_prompt = "You are a helpful assistant whose primary role is to assist business/shop owners and their employees in retrieving information and answering questions based on the documents they upload." \
            "Please give a clear and coherent answer to the user's questions.(written after \"Q:\") " \
            "using the following sources. Each source is labeled with a tag number using the format: [1], [2], etc. Feel free to " \
            "use the sources in any order, and try to use multiple sources in your answers.\n\n"
    
    system_prompt += "Sources:\n"
    for i, block in enumerate(top_blocks):
        system_prompt += f"[{i+1}] {block}\n"

    system_prompt = system_prompt.strip()



    if len(history) > 0:
        system_prompt += "\n\n"\
            "Before the question (\"Q: \"), there will be a history of previous questions and answers. " \
            "These sources only apply to the last question. Any sources used in previous answers " \
            "are invalid,  unless they are also part of the sources this time."

    prompt.append({"role": "system", "content": system_prompt.strip()})

    history_prompt = []
    for j in range(len(history)):
        query_history = {"role": "user", "content": "Q: " + history[j]["Query"]}
        response_history = {"role": "assistant", "content": history[j]["Response"]}
        history_prompt.extend([query_history, response_history])

    prompt.extend(history_prompt)

    question_prompt = f"In your answer, please cite any claims you make back to each source " \
                      f"using their respective format: [1], [2], etc. Do not reveal explicitly the association between the tags and their respective sources. " \
                      f"If you use multiple sources to make a claim cite all of them. For example: \"The milk chocolate bars are your best-selling product [c, d, e].\"\n\nQ: " + query

    prompt.append({"role": "user", "content": question_prompt})
    
    print(prompt)
    print("===================================== PROMPT CONSTRUCTED! ===================================")
    return prompt

# where the magic happens
@app.route('/app/search/<token>', methods=['POST'])
def search(token):    
    # Get the email associated with the token
    email = get_email_from_token(token)

    if email is None:
        return jsonify({'result': 'Could not find the user.'})

    data = request.json
    query = data['value'] 

    collection_history = db_history[email]

    collection_documents = db[email]
    
    pipeline = [
        { "$project": { "Blocks": 1 } },
        { "$unwind": "$Blocks" }
    ]

    cursor = collection_documents.aggregate(pipeline)

    query_emb = model.encode(query)

    top_blocks = []
    num_top_blocks = 5

    for document in cursor:
        block = document['Blocks']
        block_emb = model.encode(block)
        score = util.dot_score(query_emb, block_emb)[0].cpu().tolist()
        score = score[0]

        if len(top_blocks) < num_top_blocks:
            # If there are fewer than num_top_blocks, add the block and score directly
            heapq.heappush(top_blocks, (score, block))
        else:
            # If the current score is greater than the minimum score in top_blocks, replace the minimum score and corresponding block
            min_score = top_blocks[0][0]
            if score > min_score:
                heapq.heapreplace(top_blocks, (score, block))

    # Retrieve the top blocks from the heap in descending order of scores
    top_blocks = [block for score, block in heapq.nlargest(num_top_blocks, top_blocks)]

    _history = collection_history.find({}).sort('_id', pymongo.DESCENDING).limit(3)

    history = list(_history)

    prompt = construct_prompt(query, top_blocks, history)

    completion = openai.ChatCompletion.create(
      model="gpt-3.5-turbo",
      messages=prompt
    )
    
    print("\n")
    print(completion)
    print("\n")
    response = completion.choices[0].message.content

    record_history(collection_history, query, response)

    print(top_blocks)
    print("\n")
    return {"result": response}

if __name__ == "__main__":
    app.run(debug=True, port=5002)
