from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pickle
from scipy.sparse import load_npz
import numpy as np
import pandas as pd

class ItemRequest(BaseModel):
    itemId: str

# ==== Load Content-Based Model Files ====
with open("content_recommendation_model.sav", "rb") as f:
    content_model, content_matrix, tfidf_vectorizer = pickle.load(f)

with open("content_item_ids.pkl", "rb") as f:
    content_item_ids = pickle.load(f)
    content_item_ids = list(map(str, content_item_ids))

# ==== Load Collaborative Filtering Model Files ====
with open("collaborative.sav", "rb") as f:
    knn_model = pickle.load(f)

with open("item_mapper.sav", "rb") as f:
    raw_item_mapper = pickle.load(f)
    item_mapper = {str(k): v for k, v in raw_item_mapper.items()}

with open("item_inv_mapper.sav", "rb") as f:
    raw_item_inv_mapper = pickle.load(f)
    item_inv_mapper = {v: str(k) for k, v in raw_item_mapper.items()}

X = load_npz("X_matrix.npz")

# ==== FastAPI Setup ====
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==== Request Schema ====
class RecommendationRequest(BaseModel):
    itemId: str

# ==== Recommender Logic: Collaborative Filtering ====
def recommend_light(itemId, X, knn, item_mapper, item_inv_mapper, k=5):
    rec_ids = []

    item = item_mapper.get(itemId)
    if item is None:
        return []

    item_vector = X[item]
    rec = knn.kneighbors(item_vector.reshape(1, -1), return_distance=False)
    rec_indices = rec[0][1:k+1]

    for i in rec_indices:
        rec_ids.append(str(item_inv_mapper[i]))

    return rec_ids

@app.post("/recommend/collaborative")
def recommend(request: RecommendationRequest):
    try:
        item_id = str(request.itemId)
        recommendations = recommend_light(item_id, X, knn_model, item_mapper, item_inv_mapper)
        return {"recommendations": recommendations}
    except Exception as e:
        return {"error": str(e)}

# ==== API Endpoint: Content-Based Filtering ====
@app.post("/recommend/content")
def recommend_content(data: ItemRequest):
    try:
        item_id = str(data.itemId)

        if item_id not in content_item_ids:
            return {"recommendations": []}

        idx = content_item_ids.index(item_id)
        rec_indices = content_model.kneighbors(content_matrix[idx], n_neighbors=6, return_distance=False)
        rec_ids = [content_item_ids[i] for i in rec_indices[0] if content_item_ids[i] != item_id]

        return {"recommendations": rec_ids}

    except Exception as e:
        return {"error": str(e)}
