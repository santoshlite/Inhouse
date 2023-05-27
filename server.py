from flask import Flask, send_from_directory, request
import random
import requests
from flask import jsonify

app = Flask(__name__)

# Path for our main Svelte page
@app.route("/")
def base():
    return send_from_directory('client/public', 'index.html')

# Path for all the static files (compiled JS/CSS, etc.)
@app.route("/<path:path>")
def home(path):
    return send_from_directory('client/public', path)


@app.route("/hello")
def hello():
    return "hi"

@app.route('/print_value', methods=['POST'])
def print_value():
    data = request.json
    print(data)
    return data['value'].upper()


if __name__ == "__main__":
    app.run(debug=True, port=5002)
