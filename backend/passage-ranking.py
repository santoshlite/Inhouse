from modal import Stub, web_endpoint, Image
from typing import Dict
from sentence_transformers import SentenceTransformer, util
import numpy as np
import certifi
import os
from pymongo.mongo_client import MongoClient

stub = Stub("inhouse")

model = SentenceTransformer('sentence-transformers/msmarco-MiniLM-L6-cos-v5')

# MongoDB password
db_password = os.getenv('DB_PASSWORD')


# setting the mongodb client
uri = f"mongodb+srv://inhouse:{db_password}@inhousedb.wglo6gd.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(uri, tlsCAFile=certifi.where())

db = client["userDocuments"]

_image = (
    Image.debian_slim()
    .pip_install("sentence-transformers", "numpy", "pymongo", "certifi")
)


@stub.function(image=_image)
def magic(args: Dict):
    print("Passage reranking function called!")

    # Get query from user
    query = args["query"]

    # Encode query
    query_emb = model.encode(query)

    # Get user's documents from database
    collection_doc = db[args["email"]]

    blocks = []
    blocks_embs = []
    for document in collection_doc.find({}):
        # If embeddings are not already stored in database, compute them
        if "Embeddings" not in document or len(document["Embeddings"]) != len(document["Blocks"]):
            embeddings = [emb.tolist()
                          for emb in model.encode(document["Blocks"])]
            print("COUNT " + str(len(embeddings)))
            collection_doc.update_one({"_id": document["_id"]}, {
                                      "$set": {"Embeddings": embeddings}})

            # Convert embeddings to NumPy arrays
            embeddings = [np.array(block_emb, dtype=np.float32)
                          for block_emb in embeddings]

        # Convert existing embeddings to NumPy arrays
        else:
            embeddings = [np.array(block_emb, dtype=np.float32)
                          for block_emb in document["Embeddings"]]

        blocks.extend(document['Blocks'])

        blocks_embs.extend(document['Embeddings'])

    # Get number of blocks
    count_blocks = len(blocks)

    # Compute scores for all blocks using vectorized operation
    scores = util.dot_score(query_emb, blocks_embs).squeeze().tolist()

    # Combine docs & scores
    blocks_score_pairs = list(zip(blocks, scores))

    # Sort by decreasing score
    blocks_score_pairs = sorted(
        blocks_score_pairs, key=lambda x: x[1], reverse=True)

    # Return top 10 blocks if there are more than 10 blocks
    if count_blocks < 10:
        top_blocks = [item[0] for item in blocks_score_pairs[:count_blocks]]
    else:
        top_blocks = [item[0] for item in blocks_score_pairs[:10]]

    return {"blocks": top_blocks}
