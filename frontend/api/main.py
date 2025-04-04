from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pickle
from scipy.sparse import load_npz
import numpy as np
import pandas as pd
import requests
import json

class ItemRequest(BaseModel):
    itemId: str

# ==== Load Content-Based Model Files ====
print("[DEBUG] Loading content-based model files...")
with open("content_recommendation_model.sav", "rb") as f:
    content_model, content_matrix, tfidf_vectorizer = pickle.load(f)

with open("content_item_ids.pkl", "rb") as f:
    content_item_ids = pickle.load(f)
    content_item_ids = list(map(str, content_item_ids))

print("[DEBUG] Finished loading content-based model files. "
      f"Number of content_item_ids: {len(content_item_ids)}")

# ==== Load Collaborative Filtering Model Files ====
print("[DEBUG] Loading collaborative filtering model files...")
with open("collaborative.sav", "rb") as f:
    knn_model = pickle.load(f)

with open("item_mapper.sav", "rb") as f:
    raw_item_mapper = pickle.load(f)
    item_mapper = {str(k): v for k, v in raw_item_mapper.items()}

with open("item_inv_mapper.sav", "rb") as f:
    raw_item_inv_mapper = pickle.load(f)
    item_inv_mapper = {v: str(k) for k, v in raw_item_mapper.items()}

X = load_npz("X_matrix.npz")
print("[DEBUG] Finished loading collaborative filtering model files. "
      f"item_mapper size: {len(item_mapper)}, item_inv_mapper size: {len(item_inv_mapper)}")

# ==== FastAPI Setup ====
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==== Request Schemas ====
class RecommendationRequest(BaseModel):
    itemId: str

class AzureRequest(BaseModel):
    contentId: str

# ==== Recommender Logic: Collaborative Filtering ====
def recommend_light(itemId, X, knn, item_mapper, item_inv_mapper, k=5):
    rec_ids = []
    item = item_mapper.get(itemId)
    print(f"[DEBUG] In recommend_light, mapped itemId={itemId} to matrix index={item}")

    if item is None:
        print("[DEBUG] item is None, returning empty recommendation list.")
        return []

    item_vector = X[item]
    rec = knn.kneighbors(item_vector.reshape(1, -1), return_distance=False)
    rec_indices = rec[0][1 : k + 1]

    for i in rec_indices:
        mapped = item_inv_mapper.get(i)
        rec_ids.append(str(mapped))
        print(f"[DEBUG] KNN neighbor index={i}, mapped back to itemId={mapped}")

    return rec_ids

@app.post("/recommend/collaborative")
def recommend(request: RecommendationRequest):
    try:
        item_id = str(request.itemId)
        print(f"[DEBUG] /recommend/collaborative called with item_id={item_id}")
        recommendations = recommend_light(item_id, X, knn_model, item_mapper, item_inv_mapper)
        print("[DEBUG] Collaborative filtering recommendations:", recommendations)
        return {"recommendations": recommendations}
    except Exception as e:
        print("[ERROR] collaborative endpoint:", e)
        return {"error": str(e)}


# ==== API Endpoint: Content-Based Filtering ====
@app.post("/recommend/content")
def recommend_content(data: ItemRequest):
    try:
        item_id = str(data.itemId)
        print(f"[DEBUG] /recommend/content called with item_id={item_id}")

        if item_id not in content_item_ids:
            print("[DEBUG] item_id not in content_item_ids, returning empty list")
            return {"recommendations": []}

        idx = content_item_ids.index(item_id)
        rec_indices = content_model.kneighbors(content_matrix[idx], n_neighbors=6, return_distance=False)
        rec_ids = [content_item_ids[i] for i in rec_indices[0] if content_item_ids[i] != item_id]

        print("[DEBUG] Content-based filtering recommendations:", rec_ids)
        return {"recommendations": rec_ids}

    except Exception as e:
        print("[ERROR] content endpoint:", e)
        return {"error": str(e)}


# ==== API Endpoint: Azure ====
@app.post("/recommend/azure")
async def recommend_azure(request: Request):
    try:
        body = await request.json()
        print("[DEBUG] /recommend/azure called with body:", body)

        content_id = body.get("contentId")
        if not content_id:
            print("[DEBUG] Missing 'contentId' in request body, returning error.")
            return {"error": "Missing 'contentId' in request body"}

        # Hard-coded example (adjust userId/contentId as needed):
        azure_url = "http://504167d5-0cd9-4c14-b7ec-9d6eeff364d4.centralus.azurecontainer.io/score"
        azure_key = "QFTnMuhHJshuhmNIoo0srCsSlOVtETkx"

        # Using the contentId from the request body (if you want to pass it through),
        # comment out the following line, or create a new variable:
        # person_id = -1006791494035379303
        # known_good_content_id = 6013226412048763966
        
        # If you want to try the user's content_id directly:
        # known_good_content_id = int(content_id)  # if it's actually an integer
        # Or if your Azure pipeline expects a string, then remove the int().

        payload = {
            "Inputs": {
                "web_service_input": [
                    {
                        "personId": -1006791494035379303,  # Known working user ID
                        "contentId": 6013226412048763966, # Known working content ID
                        "eventRating": 5.0
                    }
                ]
            }
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {azure_key}"
        }

        print("[DEBUG] Payload sent to Azure:", json.dumps(payload, indent=2))
        response = requests.post(azure_url, headers=headers, json=payload)

        # Extra logging for status code and raw text
        print("[DEBUG] Azure response status code:", response.status_code)
        print("[DEBUG] Azure response raw text:", response.text)

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as http_err:
            print("[DEBUG] Azure response text on HTTPError:", response.text)
            raise http_err

        result = response.json()
        print("[DEBUG] Full Azure response (parsed JSON):", json.dumps(result, indent=2))

        # Explore possible places for the recommended items
        output = result.get("Results", {}).get("output1", [])
        scored_results = result.get("Results", {}).get("Scored Results", [])
        print("[DEBUG] output1 contents:", json.dumps(output, indent=2))
        print("[DEBUG] Scored Results contents:", json.dumps(scored_results, indent=2))

        # We'll pick whichever is not empty
        recommendations = output or scored_results or []
        print("[DEBUG] final recommendations chosen:", recommendations)

        return {"recommendations": recommendations}

    except Exception as e:
        print("[❌] Azure recommend error:", e)
        return {"error": str(e)}
