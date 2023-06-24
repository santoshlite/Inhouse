from __future__ import print_function
from flask import Flask, send_from_directory, request, jsonify, redirect, Response, stream_with_context
from g_drive_service import GoogleDriveService
from flask_cors import CORS
import gdown
import time
import pymongo
from pymongo.mongo_client import MongoClient
import itertools
from markupsafe import Markup
import certifi
import modal
import secrets
import textract
import json
import openai
import os
import re

# OpenAI API key
openai.api_key = os.getenv('OPENAI_API_KEY')

# MongoDB password
db_password = os.getenv('DB_PASSWORD')

# Frontend url
frontend_url = os.getenv('APP_DOMAIN')

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

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
    return redirect(frontend_url)

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

    return closest_directory


# Helper function that replace tags 
def replace_tags(text):
    pattern = r'\[(\d+)\]'  # regex pattern to match [number]

    def replace(match):
        number = match.group(1)
        return '{' + number + '}'  # Replace [number] with {number}

    modified_text = re.sub(pattern, replace, text)
    return modified_text

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
    global token
    # retrieve the email and password from the form
    email = request.form['email']
    password = request.form['password']

    # check if the user already exists
    existing_token = get_token_from_email(email)
    existing_password = get_password_from_email(email)

    # if the user exists and the password is correct, redirect to the app
    if existing_token and existing_password == password:
        token = existing_token
        return redirect(f"{frontend_url}home/")
    
    # if the user exists but the password is incorrect, redirect to the auth page
    elif existing_token and existing_password != password:
        return redirect(f"{frontend_url}auth?error=wrong_password")

    # if the user does not exist, create a new user and token, store its password
    else:
        token = generate_token()
        associate_email_with_token(token, email, password)

    return redirect(f"{frontend_url}home/")

# get the number of files uploaded by the user -> to display under search bar
@app.route("/home/get_uploaded_count/")
def get_uploaded_count():
    email = get_email_from_token(token)

    if email is None:
        return "Invalid token"
    
    collection = db[email]
    uploaded_files = collection.count_documents({})
    return str(uploaded_files)


# add file to the database
def update_mongo_record(collection, fileName, text, blocks, modifiedDate, version):
    uploadFile = {
        "FileName": fileName,
        "Content": text,
        "Blocks": blocks, 
        "ModifiedDate" : modifiedDate,
        "Version" : version
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
@app.route("/home/get_history_list/")
def get_history_list():
    email = get_email_from_token(token)

    if email is None:
        return jsonify({"error": "Invalid token"})
    
    history_collection = db_history[email]
    history_documents = history_collection.find({}).sort("_id", pymongo.DESCENDING)

    query_list = [doc["Query"] for doc in history_documents]

    return jsonify({"queries": query_list})


@app.route("/home/get_response_from_query/", methods=['POST'])
def get_response_from_query():
    responseValue = "Loading response..."
    data = request.json
    query = data['value']

    # Get the email associated with the token
    email = get_email_from_token(token)
    history_collection = db_history[email]

    if email is None:
        return jsonify({'result': 'Invalid token', 'blocks': []})
    
    # Find the most recent document in the collection that matches the query
    result = history_collection.find_one({'Query': query})

    if result:
        return result['Response']
    else:
        return jsonify({'result': 'No response found', 'blocks': []})

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
            blocks.append("{" + docname + "}" + " - " + current_block.strip())
            current_block = sentence + " "

    if current_block:
        blocks.append("{" + docname + "}" + " - " + current_block.strip())

    return blocks

def upload_single_file(file, collection):
    print("===================================== STEP 1: ENTERED UPLOAD SINGLE FILE! ===================================")
    filename = file.filename
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)

    text = textract.process(file_path).decode('utf-8')
    text = replace_tags(text)

    name, extension = os.path.splitext(filename)
    text_file_path = os.path.join(app.config['UPLOAD_FOLDER'], name + ".txt")

    with open(text_file_path, "w") as text_file:
        text_file.write(text)

    # Get the blocks from the file
    blocks = file_to_blocks(text, 300, filename)

    # Remove the uploaded files
    os.remove(file_path)
    os.remove(text_file_path)

    # Search for documents with the specified filename
    fileExist = collection.find_one({"FileName": filename})

    # Check if a document was found
    if fileExist is not None:
        update_mongo_record(collection, filename + "#", text, blocks, "no need for modified time", "no need for version number")
    else:
        update_mongo_record(collection, filename, text, blocks, "no need for modified time", "no need for version number")

    print("===================================== STEP 2: UPDATED MONGO RECORD! ===================================")


@app.route('/home/upload_file/', methods=['POST'])
def upload_file():
    # Get the email associated with the token
    email = get_email_from_token(token)

    if email is None:
        return jsonify({'Message': 'Invalid token'})

    # Get the collection based on the email
    collection = db[email]

    print("===================================== STEP 4: ENTERED UPLOAD_FILE ===================================")
    files = request.files.getlist('files[]')
    uploaded_files = []

    for file in files:
        print(file.filename)
        upload_single_file(file, collection)
        filename = file.filename
        uploaded_files.append(filename)

    print("===================================== STEP 5: FINAL STAGE ===================================")
    return jsonify({'Message': f'{len(uploaded_files)} Files uploaded successfully'})



# This function gets all the files underneath a certain folder containing a given ID 
@app.get('/files-in-folder/<folder_id>/')
def get_files_in_folder(folder_id):
    
    selected_field="files(id, name, webViewLink, version, modifiedTime)"
    query=f" '{folder_id}' in parents "
    
    list_of_files = service.files().list(
        q=query,
        fields=selected_field
    ).execute()

    name_info_dict = {}

    # Loop through list of dictionaries and retrieve name and id of each file
    for i in range(len(list_of_files["files"])):

        print(i)
        name = list_of_files["files"][i]["name"]
        id = list_of_files["files"][i]["id"]
        modifiedtime = list_of_files["files"][i]["modifiedTime"]
        version = list_of_files["files"][i]["version"]
        print("THIS IS THE VERSION =====-=-=-=-=-=-+>" + version)

        #Construct list containing useful information
        user_info = [id, modifiedtime, version]

        # Construct new dictionary
        name_info_dict[name] = user_info

    for key, value in name_info_dict.items():
        print("filename is:" + key)
        print("id is: " + value[0])
        print("modified time is: " + value[1])
        print("modified version is: " + value[2])

    return name_info_dict


# This function first download the file, then upload it to the mongo database
def upload_single_google_file(filename, list_of_info, collection):

    gdown.download("https://drive.google.com/uc?id="+ list_of_info[0], filename, quiet=False, fuzzy=True)
    
    ext = os.path.splitext(filename)[1]

    try:
        # if-else checks the extension to whether it is a google doc or not
        if ext == "":
            text = textract.process(filename, extension='docx').decode('utf-8')
        else:
            text = textract.process(filename).decode('utf-8')
    except KeyError:
        return 

    text = replace_tags(text)

    with open(filename, "w") as file:
            # Write the contents of the variable to the file
            file.write(text)
    
    # Get the blocks from the file
    blocks = file_to_blocks(text, 300, filename)
    print(filename)
    os.remove(filename)

    # update the mongo record to store appropriate information
    update_mongo_record(collection, filename, text, blocks, list_of_info[1], list_of_info[2])
    

def extract_folder_id(url):
    pattern = r'/drive/folders/([\w-]+)\b'
    match = re.search(pattern, url)
    if match and match.group(1):
        return match.group(1)
    elif match and not match:
        return match
    return None

@app.route('/home/upload_google_file/', methods=['POST'])
def upload_google_file():
# Get the email associated with the token
    email = get_email_from_token(token)

    data = request.json
    url_folder = data['url'] 

    folder_id = extract_folder_id(url_folder)


    if email is None:
        return jsonify({'Message': 'Invalid token'})

    # Get the collection based on the email
    collection = db[email]

    user_data = db["token_email_mapping"].find_one({"email": email})

    if user_data:
        if "folder_id" in user_data:
            if folder_id in user_data["folder_id"]:
                return jsonify({'Message': 'Folder ID already exists.'})
            else:
                # Append folder_id to the existing list
                db["token_email_mapping"].update_one({"email": email}, {"$addToSet": {"folder_id": folder_id}})
        else:
            # Create a new list with folder_id as the only element
            db["token_email_mapping"].update_one({"email": email}, {"$set": {"folder_id": [folder_id]}})


    # upload_multiple_google_file(folder_id, collection)
  
    name_info_dictionary = get_files_in_folder(folder_id)

    # for loop that loops through the dictionary of google files and gives the file name and its corresponding list for each
    for key, value in name_info_dictionary.items():
        upload_single_google_file(key, value, collection)


    print("===================================== STEP 5: FINAL STAGE ===================================")
    return jsonify({'Message': f'Google Files uploaded successfullly.'})


#
#
# ===================================================== SYNCING GOOGLE DOC ======================================================
#
#

@app.route('/home/sync_google/')
def sync_google():
    print("SYNC")
    # Get the email associated with the token
    email = get_email_from_token(token)
    print("EMAIL" + email)
    user_data = db["token_email_mapping"].find_one({"email": email})

    if user_data and "folder_id" in user_data:
            print("SOMETHING")
            folder_ids = user_data["folder_id"]
            for folder_id in folder_ids:
                print(folder_id)
                sync_google_files(token, folder_id)
            return jsonify({'Message': 'Google Drive synced successfullly'})
    else:
        print("NOTHING")
        return jsonify({'Message': 'X'})


def sync_google_files(token, folder_id):

    # Get the email associated with the token
    email = get_email_from_token(token)

    if email is None:
        return jsonify({'Message': 'Invalid token'})

    # Get the collection based on the email
    collection = db[email]

    past_name_infoList_dictionary = {}

    # MAJOR STEP: loop through the database and retreieve values of modified dates
    for x in collection.find({}, {"FileName" : 1, "ModifiedDate" : 1, "Version" : 1}):

        # constructing the list of info!
        # value[0] MUST CORRESPOND TO ID NUMBER 
        # value[1] MUST CORRESPOND TO MODIFIED DATE
        # value[2] MUST CORRESPOND TO VERSION
        temp_list_of_info = [x['_id'], x['ModifiedDate'], x['Version']]

        # updating dictionary!!!
        past_name_infoList_dictionary[x['FileName']] = temp_list_of_info
        
    #
    # At this point, I successfully retrieved info from mongodatabase and have it stored in a dictionary
    #


    # Retrieving current google doc information => simply call the previously defined function
    current_name_info_dictionary = get_files_in_folder(folder_id)


    # For loop that goes through the current dictionary => since this is the most important 
    for key, value in current_name_info_dictionary.items():

        # Now, retreive current and past list of info for each key entry in the dictionary
        current_single_list_of_info = value
        past_single_list_of_info = past_name_infoList_dictionary.get(key)

        # something to keep in mind:
        #
        # The current_single_list_of_info architecture is as follows:  ['1qQwuE0IeSenVunWXrilsxfF--hV-KeZQaQ2EO7nDsvA', '2023-06-05T10:23:36.357Z', '12']
        #
        # The past_single_list_of_info architecture is as follows:    [ObjectId('647de796104f971dadd33ca6'), '2023-06-05T10:23:36.357Z', '12']
        #
        #


# case 1: user created a new doc!!!!!
        
        # if statement checks if list is empty
        if(not past_single_list_of_info):

            # First step: get both content and blocks from the file so I UPDATE THEM!!!!!
            file_id = current_single_list_of_info[0]
            filename = key

            gdown.download("https://drive.google.com/uc?id="+ file_id, filename, quiet=False, fuzzy=True)
            ext = os.path.splitext(filename)[1]

            try:
                # if-else checks the extension to whether it is a google doc or not
                if ext == "":
                    text = textract.process(filename, extension='docx').decode('utf-8')
                else:
                    text = textract.process(filename).decode('utf-8')
            except KeyError:
                return 
    
            text = replace_tags(text)

            with open(filename, "w") as file:
                # Write the contents of the variable to the file
                file.write(text)
    
            # Get the blocks from the file
            blocks = file_to_blocks(text, 300, filename)

            os.remove(filename)

            # INSERTING THE DOC
            collection.insert_one(
                {
                    'FileName': filename,
                    'Content' : text,
                    'Blocks' : blocks, 
                    'ModifiedDate' : current_single_list_of_info[1],
                    'Version' : current_single_list_of_info[2]
                }
            )

        else:
            # Now, I know user has a pre-existing list of info so I need to check if it is modified or not

            if(current_single_list_of_info[1] != past_single_list_of_info[1]):

                # First step: get both content and blocks from the file so I UPDATE THEM!!!!!
                file_id = current_single_list_of_info[0]
                filename = key

                gdown.download("https://drive.google.com/uc?id="+ file_id, filename, quiet=False, fuzzy=True)
                ext = os.path.splitext(filename)[1]

                # if-else checks the extension to whether it is a google doc or not
                if ext == "":
                    text = textract.process(filename, extension='docx').decode('utf-8')
                else:
                    text = textract.process(filename).decode('utf-8')

                text = replace_tags(text)

                with open(filename, "w") as file:
                    # Write the contents of the variable to the file
                    file.write(text)
    
                # Get the blocks from the file
                blocks = file_to_blocks(text, 300, filename)

                os.remove(filename)


                # NOW, the updated variables are as follows:
                # Content => text
                # Blocks  => blocks
                # ModifiedDate => current_single_list_of_info[1]
                # Version => current_single_list_of_info[2]

                # With this, I update the collection in the following:

                # Define the filter criteria as the object id in the mongodb => ALWAYS UNIQUE
                #
                filter_criteria = {
                    '_id' : past_single_list_of_info[0]
                }
                
                
                # Define the update operation
                update_operation = {
                    '$set': {
                        'Content' : text,
                        'Blocks' : blocks, 
                        'ModifiedDate' : current_single_list_of_info[1],
                        'Version' : current_single_list_of_info[2]
                    }
                }
                
                collection.update_one(filter_criteria, update_operation)

    # For loop that goes through the past dictionary => this is to search if user have removed a doc
    for key, value in past_name_infoList_dictionary.items():
        past_single_list_of_info = value
        current_single_list_of_info = current_name_info_dictionary.get(key)

        # Checks if the current google doc contains all documents from the past
        if(not current_single_list_of_info):


            # Only delete if the document IS INDEED FROM GOOGLE DRIVE! => This only require checking modified date
            if(past_single_list_of_info[1] != ("no need for modified time")):

                # If the value does not exist in current google doc, do this:
                criteria = {
                    "_id": past_single_list_of_info[0]
                }

                collection.delete_one(criteria)

    return jsonify({'Message': f'Google Files synced successfullly'})

######################################
#####################################
#####################################


def call_llm(prompt):
    max_retries = 5
    retry_count = 0
    wait_time = 1

    while retry_count < max_retries:
        try:
            completion = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=prompt
            )
            
            response = completion.choices[0].message.content.strip()

            return response  # Return the response if the API call is successful

        except Exception as e:
            print(f"Error occurred: {str(e)}")
            print(f"Retrying in {wait_time} seconds...")
            time.sleep(wait_time)

            # Increase the wait time exponentially for the next retry
            wait_time *= 2
            retry_count += 1

def construct_prompt(query, top_blocks, history):

    prompt = []

    system_prompt = "You are a helpful document assistant whose primary role is to assist people in retrieving information, answering questions, and generating things from the documents given." \
            "Please give a clear and coherent answer to the user's questions. (written after \"Q:\") " \
            "using the following sources. Each source is labeled with a tag number using the format: [1], [2], etc. Feel free to " \
            "use the sources in any order, and try to use multiple sources in your answers.\n\n"
    
    system_prompt += "Sources:\n"
    for i, block in enumerate(top_blocks):
        system_prompt += f"[{i+1}] {block}\n"
        print(f"[{i+1}] {block}\n")

    system_prompt = system_prompt.strip()



    if len(history) > 0:
        system_prompt += "\n\n"\
            "Before the question (\"Q: \"), there will be a history of previous questions and answers. " \
            "These sources only apply to the last question. Any sources used in previous answers " \
            "are invalid."

    prompt.append({"role": "system", "content": system_prompt.strip()})

    history_prompt = []
    for j in range(len(history)):
        query_history = {"role": "user", "content": "Q: " + history[j]["Query"]}
        response_history = {"role": "assistant", "content": history[j]["Response"]["result_plain"]}
        history_prompt.extend([query_history, response_history])

    prompt.extend(history_prompt)

    question_prompt = f"In your answer, please cite any claims you make back to each source " \
                      f"using the format: [a], [b], etc. Although you must indicate the sources you use using the format discussed previously, you should not explicitly show or list your sources e.g., links, file name." \
                      f"If you use multiple sources to make a claim cite all of them. " \
                      f"For example: \"The milk chocolate bars are your best-selling product [1] [2] [3].\"\n\nQ: " + query

    prompt.append({"role": "user", "content": question_prompt})
    
    print(prompt)
    print("===================================== PROMPT CONSTRUCTED! ===================================")
    return prompt


# where the magic happens
@app.route('/home/search/', methods=['POST'])
def search():    
    # Get the email associated with the token
    email = get_email_from_token(token)
    
    response = Response(stream_with_context(generate_response(email)))
    response.headers['Content-Type'] = 'application/x-ndjson'
    return response

def generate_response(email):

    yield json.dumps({"status": "Looking for most relevant blocks..."}) 
    data = request.json
    query = data['value'] 

    collection_history = db_history[email]
    
    data = {
        "query": query,
        "email": email
    }

    print("MODAL TIME")
    f = modal.Function.lookup("inhouse", "magic")
    top_blocks = f.call(data)

    yield json.dumps({"status": "Crafting prompt..."}) 
    
    _history = collection_history.find({}).sort('_id', pymongo.DESCENDING).limit(3)

    history = list(_history)

    prompt = construct_prompt(query, top_blocks, history)

    yield json.dumps({"status": "Generating response..."}) 
    response = call_llm(prompt)

    print("===================================== RESPONSE FROM GPT-3 ===================================")
    print(response)
    print("===================================== END RESPONSE FROM GPT-3 ===================================")

    yield json.dumps({"status": "Cleaning response..."}) 
    output = {"blocks": []}

    tags = re.findall(r"\[(\d+)\]", response)

    unique_tags = []
    seen = set()

    for tag in tags:
        if tag not in seen:
            seen.add(tag)
            unique_tags.append(tag)

    print(unique_tags)
    
    style = ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"]

    # Truncate style list to match the length of unique_tags
    truncated_style = list(itertools.islice(style, len(unique_tags)))

    # Mapping document name to blocks that were used
    for index, (tag, s) in enumerate(zip(unique_tags, truncated_style)):
        block = top_blocks[int(tag)-1]
        document_name = re.search(r"{([^}]+)} - ", block)
        document_name = document_name.group(1)
        block = block.replace("{"+document_name+"}" + " - ", "") 
        # Check if text starts with a lowercase letter
        if block[0].islower():
            block = "[...] " + block

        # Check if text doesn't end with a period
        if block and not block.endswith("."):
            block += " [...]"    

        output["blocks"].append({"document_name": document_name, "block": block, "tag": f"<span class='{s}' id='tag-{s}'>[" + str(index+1) + "]</span>"})


    # Mapping tags to order of appearance -> Re-indexing tags to start from 1
    tag_mapping = {}
    for i, (tag,s) in enumerate(zip(unique_tags, truncated_style), start=1):
        print(tag, i)
        tag_mapping[tag] = f"<span class='{s}' onclick=\"scrollToElement('tag-{s}')\">[{str(i)}]</span>"

    final_response = re.sub(r"\[(\d+)\]", lambda match: "{}".format(tag_mapping.get(match.group(1), match.group(1))), response)
    
    output["result_plain"] = response

    output["result"] = Markup("<pre class='response'>"+final_response +"</pre>") 

    output["query"] = query

    record_history(collection_history, query, output)

    yield json.dumps({"status" : "Done", "response": output}) 

if __name__ == "__main__":
    app.run(debug=True, port=8000, ssl_context='adhoc')

