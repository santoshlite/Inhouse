![repo-picture](https://github.com/ssantoshp/inhouse/assets/61618641/c41f75f5-602c-4469-97ed-01916dab94fc)
## What is Inhouse
Inhouse is a **user-friendly** and **intuitive document assistant** that helps you improve your **productivity**. Inhouse integrates **seamlessly** with your **Google Drive**, allowing you to ask questions about your documents using **natural language**. It **answers your questions** effortlessly and **provides sources** from your documents, making knowledge retrieval a breeze.

Built with:
<p align="center">
  <img width="700" src="https://iili.io/H6ZzLtS.png">
</p>

## How does it work
1. Go to [**Inhouse**](https://inhouse.up.railway.app/)
2. Create an account
3. Upload files or give a sharing link to one of your Google Drive folders by clicking on "Sync Drive"
4. Shoot your questions!

## Demo
https://github.com/ssantoshp/inhouse/assets/61618641/c4e102c6-d08b-47e3-af5a-f482a505d08c


## How to run it locally
1. Git clone the repo
2. Setting up the frontend
    - Go to the `frontend` directory
    - Make sure to use node 18 (use `nvm` if you have another version)
    - Run `npm i`
    - Create a `.env` file and set `VITE_API_DOMAIN` to the url of the flask server
    - Run `npm run dev` will start the server
3. Setting up the backend
    - Go to the `backend` directory
    - `pip install -r requirements.txt`
    - Set up a MongoDB cluster and replace the connection string on `main.py`
    - Make the `passage-ranking.py` file a Modal instance (more info [here](https://modal.com/docs/guide/trigger-deployed-functions))
    - Creare a `.env` file and set the variables `OPENAI_API`, `DB_PASSWORD` and `APP_DOMAIN` (url of the vite server)
    - Run `python3 main.py`
4. Boom! You should be good to go but if you face a problem, feel free to make an issue :))

## Credits
This project was greatly inspired from [AlignmentSearch](https://github.com/FraserLee/AlignmentSearch) made by [Fraser Lee](https://github.com/FraserLee), [Henri Lemoine](https://github.com/henri123lemoine) and [Thomas Lemoine](https://github.com/Thomas-Lemoine). 

We've basically used their OpenAI API prompt and tuned it a bit for our use case!
