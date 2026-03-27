# ============================================================
# Crop Yield Predictor API
# Built with FastAPI + scikit-learn
# This file defines all the endpoints for making predictions,
# retraining the model, and serving model metadata.
# ============================================================

import os
import io
import json
import datetime
import pandas as pd
import joblib
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import List, Optional
from sklearn.metrics import r2_score, mean_squared_error
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split

# Create the FastAPI app instance
# This is the main entry point for all our API endpoints
app = FastAPI()

# ─ CORS Middleware ──────────────────────────────────────────────────────────
# CORS (Cross-Origin Resource Sharing) allows our Flutter app and other
# clients to talk to this API from different origins/domains.
# Instead of using allow_origins=["*"] (which allows everyone),
# we specify exactly which origins are allowed for better security.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://crop-yield-predictor-api-nhma.onrender.com",  # our deployed API
        "http://localhost",        # local development
        "http://localhost:8080",   # Flutter web local dev
        "http://127.0.0.1",        # alternative localhost
    ],
    allow_credentials=True,                        # allow cookies/auth headers
    allow_methods=["GET", "POST"],                 # only the methods we actually use
    allow_headers=["Content-Type", "Authorization"],  # only the headers we need
)

# ── Valid Input Values ───────────────────────────────────────────────────────
# These are the exact countries and crops the model was trained on.
# If a user sends a value outside these lists, we return a helpful error
# instead of letting the model crash or give a nonsense prediction.
VALID_AREAS = [
    "Albania", "Algeria", "Angola", "Argentina", "Armenia", "Australia",
    "Austria", "Azerbaijan", "Bahamas", "Bahrain", "Bangladesh", "Belarus",
    "Belgium", "Botswana", "Brazil", "Bulgaria", "Burkina Faso", "Burundi",
    "Cameroon", "Canada", "Central African Republic", "Chile", "Colombia",
    "Croatia", "Denmark", "Dominican Republic", "Ecuador", "Egypt",
    "El Salvador", "Eritrea", "Estonia", "Finland", "France", "Germany",
    "Ghana", "Greece", "Guatemala", "Guinea", "Guyana", "Haiti", "Honduras",
    "Hungary", "India", "Indonesia", "Iraq", "Ireland", "Italy", "Jamaica",
    "Japan", "Kazakhstan", "Kenya", "Latvia", "Lebanon", "Lesotho", "Libya",
    "Lithuania", "Madagascar", "Malawi", "Malaysia", "Mali", "Mauritania",
    "Mauritius", "Mexico", "Montenegro", "Morocco", "Mozambique", "Namibia",
    "Nepal", "Netherlands", "New Zealand", "Nicaragua", "Niger", "Norway",
    "Pakistan", "Papua New Guinea", "Peru", "Poland", "Portugal", "Qatar",
    "Romania", "Rwanda", "Saudi Arabia", "Senegal", "Slovenia", "South Africa",
    "Spain", "Sri Lanka", "Sudan", "Suriname", "Sweden", "Switzerland",
    "Tajikistan", "Thailand", "Tunisia", "Turkey", "Uganda", "Ukraine",
    "United Kingdom", "Uruguay", "Zambia", "Zimbabwe"
]

VALID_CROPS = [
    "Cassava", "Maize", "Plantains and others", "Potatoes", "Rice paddy",
    "Sorghum", "Soybeans", "Sweet potatoes", "Wheat", "Yams"
]

# Build lowercase lookup maps so we can do case-insensitive matching
# e.g. "rwanda" and "RWANDA" both map to "Rwanda"
_AREA_MAP = {a.lower(): a for a in VALID_AREAS}
_CROP_MAP = {c.lower(): c for c in VALID_CROPS}

# Path to the folder where our trained model files (.pkl) are stored
# We go one directory up from the API folder to reach linear_regression/
ARTIFACTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "linear_regression")

# ── Auto-Retrain Configuration ───────────────────────────────────────────────
# Instead of retraining manually every time, we automatically trigger
# retraining after every AUTO_RETRAIN_THRESHOLD predictions.
# Each prediction is buffered and used as new training data.
AUTO_RETRAIN_THRESHOLD = 100   # retrain after 100 new predictions
new_data_buffer: List[dict] = []  # stores incoming prediction data
prediction_counter = 0            # counts predictions since last retrain
# ────────────────────────────────────────────────────────────────────────────


# ── Model Artifacts Container ────────────────────────────────────────────────
# This class holds all the loaded model objects in memory so we don't
# have to reload from disk on every single request (that would be slow).
class ModelArtifacts:
    model: Optional[RandomForestRegressor] = None
    scaler: Optional[StandardScaler] = None
    le_area: Optional[LabelEncoder] = None  # encoder for country names
    le_item: Optional[LabelEncoder] = None  # encoder for crop names
    metadata: dict = {}                      # stores r2, rmse, retrain time

artifacts = ModelArtifacts()


def load_artifacts():
    """
    Load the trained model and preprocessing objects from disk.
    Called once when the API starts up.
    If any file is missing, we print a warning instead of crashing.
    """
    try:
        artifacts.model  = joblib.load(os.path.join(ARTIFACTS_DIR, "best_model.pkl"))
        artifacts.scaler = joblib.load(os.path.join(ARTIFACTS_DIR, "scaler.pkl"))

        # label_encoders.pkl stores both encoders in one dict: {'Area': ..., 'Item': ...}
        label_encoders    = joblib.load(os.path.join(ARTIFACTS_DIR, "label_encoders.pkl"))
        artifacts.le_area = label_encoders['Area']
        artifacts.le_item = label_encoders['Item']

        # Load metadata like r2_score and rmse that we saved after training
        with open(os.path.join(ARTIFACTS_DIR, "model_metadata.json"), "r") as f:
            artifacts.metadata = json.load(f)

        print(" Model artifacts loaded successfully.")
    except Exception as e:
        print(f"Warning: Failed to load some artifacts: {e}")


@app.on_event("startup")
def startup_event():
    """
    This runs automatically when the API server starts.
    We load the model here so it's ready before any requests come in.
    """
    load_artifacts()


# ── Input/Output Schemas ─────────────────────────────────────────────────────
# Pydantic BaseModel does two things for us:
# 1. Enforces data types (e.g. year must be int, not a string)
# 2. Validates ranges (e.g. temperature can't be 500°C)
# If validation fails, FastAPI automatically returns a 422 error with details.

class PredictionRequest(BaseModel):
    area: str = Field(
        "Rwanda",
        description="Country name (must be one of the values returned by /areas).",
    )
    item: str = Field(
        "Maize",
        description="Crop type (must be one of the values returned by /crops).",
    )
    year: int = Field(2020, ge=1990, le=2030, description="Year (1990–2030).")
    average_rain_fall_mm_per_year: float = Field(
        1200.0, ge=51.0, le=3240.0, description="Average annual rainfall in mm."
    )
    pesticides_tonnes: float = Field(
        10.0, ge=0.0, le=400000.0, description="Pesticide usage in tonnes."
    )
    avg_temp: float = Field(
        25.0, ge=1.3, le=30.65, description="Average temperature in °C."
    )

    @validator('area')
    def validate_area(cls, v):
        # First try exact match, then try case-insensitive match
        if v in VALID_AREAS:
            return v
        normalized = _AREA_MAP.get(v.lower())
        if normalized:
            return normalized
        # If still not found, return a helpful error message
        raise ValueError(
            f"Unknown country: '{v}'. "
            f"See the /areas endpoint for all {len(VALID_AREAS)} supported countries."
        )

    @validator('item')
    def validate_item(cls, v):
        # Same case-insensitive matching logic for crop type
        if v in VALID_CROPS:
            return v
        normalized = _CROP_MAP.get(v.lower())
        if normalized:
            return normalized
        raise ValueError(
            f"Unknown crop: '{v}'. "
            f"Valid crops are: {', '.join(sorted(VALID_CROPS))}."
        )


class PredictionResponse(BaseModel):
    """What the API returns after a successful prediction."""
    prediction: float = Field(..., description="The predicted yield (hg/ha).")
    predicted_yield_hg_per_ha: float = Field(
        ...,
        description="Same as `prediction` (kept for backwards compatibility).",
    )
    area: str
    item: str
    year: int
    model_type: str        # tells the user which model made the prediction
    model_r2_score: float  # so users know how accurate the model is
    timestamp: str         # when the prediction was made

    class Config:
        schema_extra = {
            "example": {
                "prediction": 51234.56,
                "predicted_yield_hg_per_ha": 51234.56,
                "area": "Rwanda",
                "item": "Maize",
                "year": 2020,
                "model_type": "Random Forest",
                "model_r2_score": 0.87,
                "timestamp": "2026-03-27T12:00:00",
            }
        }


# ── Basic Endpoints ──────────────────────────────────────────────────────────

@app.get("/")
def read_root():
    """Welcome message — just to confirm the API is alive."""
    return {"message": "Welcome to the Crop Yield Predictor API", "docs": "/docs"}


@app.get("/health")
def health_check():
    """
    Health check endpoint — useful for monitoring and debugging.
    Also shows auto-retrain progress so we can see how many
    predictions have been collected since the last retrain.
    """
    return {
        "status": "healthy" if artifacts.model is not None else "model_missing",
        "r2_score": artifacts.metadata.get("r2_score"),
        "rmse":     artifacts.metadata.get("rmse"),
        "predictions_since_last_retrain": prediction_counter,
        "retrain_threshold":              AUTO_RETRAIN_THRESHOLD,
        "buffered_new_samples":           len(new_data_buffer),
        "valid_crops": VALID_CROPS,
        "timestamp":   datetime.datetime.now().isoformat()
    }


@app.get("/areas")
def get_areas():
    """Returns the list of all valid country names the model supports."""
    return VALID_AREAS


@app.get("/crops")
def get_crops():
    """Returns the list of all valid crop types the model supports."""
    return VALID_CROPS


# ── Core Retraining Logic ────────────────────────────────────────────────────

def do_retrain(csv_content: bytes):
    """
    Retrains the Random Forest model using new + existing data.
    
    Steps:
    1. Load the new data from CSV bytes
    2. Combine it with the original training data (if available)
    3. Re-encode categories, re-scale features
    4. Train a new Random Forest model
    5. Save everything back to disk and reload into memory
    
    This function runs in the background so it doesn't block the API.
    """
    try:
        df_new = pd.read_csv(io.BytesIO(csv_content))

        # Try to load the original dataset and combine with new data
        orig_csv_path = os.path.join(ARTIFACTS_DIR, "yield_df.csv")
        if os.path.exists(orig_csv_path):
            df_orig     = pd.read_csv(orig_csv_path)
            df_combined = pd.concat([df_orig, df_new], ignore_index=True)
        else:
            # No original data found — just use the new data
            df_combined = df_new

        # Re-encode categorical columns (country and crop) as numbers
        # because ML models can't work with raw strings
        le_area = LabelEncoder()
        le_item = LabelEncoder()
        df_combined['Area'] = le_area.fit_transform(df_combined['Area'])
        df_combined['Item'] = le_item.fit_transform(df_combined['Item'])

        # Separate features (X) from target variable (y)
        X = df_combined[['Area', 'Item', 'Year',
                          'average_rain_fall_mm_per_year',
                          'pesticides_tonnes', 'avg_temp']]
        y = df_combined['hg/ha_yield']

        # Scale features to zero mean and unit variance
        # This helps the model converge faster and more accurately
        scaler   = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # 80/20 train-test split to evaluate the retrained model
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=0.2, random_state=42)

        # Train a new Random Forest model
        model = RandomForestRegressor(
            n_estimators=50, max_depth=10, random_state=42, n_jobs=-1)
        model.fit(X_train, y_train)

        # Evaluate performance on the test set
        preds    = model.predict(X_test)
        new_r2   = float(r2_score(y_test, preds))
        new_rmse = float(mean_squared_error(y_test, preds, squared=False))

        # Save updated model files back to disk
        os.makedirs(ARTIFACTS_DIR, exist_ok=True)
        joblib.dump(model,  os.path.join(ARTIFACTS_DIR, "best_model.pkl"))
        joblib.dump(scaler, os.path.join(ARTIFACTS_DIR, "scaler.pkl"))
        joblib.dump({'Area': le_area, 'Item': le_item},
                    os.path.join(ARTIFACTS_DIR, "label_encoders.pkl"))

        # Save updated metadata with new scores and retrain timestamp
        meta = {
            "r2_score":    new_r2,
            "rmse":        new_rmse,
            "retrained_at": datetime.datetime.now().isoformat()
        }
        with open(os.path.join(ARTIFACTS_DIR, "model_metadata.json"), "w") as f:
            json.dump(meta, f)

        # Save the combined dataset for future retrains
        df_combined.to_csv(orig_csv_path, index=False)

        # Reload the new model into memory so predictions use it immediately
        artifacts.model    = model
        artifacts.scaler   = scaler
        artifacts.le_area  = le_area
        artifacts.le_item  = le_item
        artifacts.metadata = meta

        print(f" Retraining complete — R²: {new_r2:.4f}, RMSE: {new_rmse:.2f}")
    except Exception as e:
        print(f" Retraining failed: {e}")


def auto_retrain_if_ready(background_tasks: BackgroundTasks):
    """
    This is called after every prediction to check if we've
    collected enough new data to trigger an automatic retrain.
    
    How it works:
    - Every prediction gets added to new_data_buffer
    - When the buffer reaches AUTO_RETRAIN_THRESHOLD (100),
      we convert it to CSV and kick off retraining in the background
    - The counter and buffer are then reset to start fresh
    
    Using the predicted yield as the label isn't perfect, but it
    allows the model to continuously adapt to new usage patterns.
    """
    global prediction_counter, new_data_buffer

    prediction_counter += 1

    if prediction_counter >= AUTO_RETRAIN_THRESHOLD:
        print(f" Auto-retrain triggered after {prediction_counter} predictions.")
        df_new    = pd.DataFrame(new_data_buffer)
        csv_bytes = df_new.to_csv(index=False).encode("utf-8")

        # Run retraining in the background — doesn't block the API response
        background_tasks.add_task(do_retrain, csv_bytes)

        # Reset for the next cycle
        prediction_counter = 0
        new_data_buffer    = []


# ── Helper: Run a Single Prediction ─────────────────────────────────────────

def _make_prediction(req: PredictionRequest) -> float:
    """
    Encode the input, scale it, and run it through the model.
    Returns the predicted yield in hg/ha as a float.
    """
    if not artifacts.model:
        raise HTTPException(status_code=500, detail="Models are not loaded.")
    try:
        # Convert country/crop strings to the numeric codes the model expects
        area_enc = artifacts.le_area.transform([req.area])[0]
        item_enc = artifacts.le_item.transform([req.item])[0]

        # Build a single-row DataFrame matching the training feature order
        df_features = pd.DataFrame([[
            area_enc, item_enc, req.year,
            req.average_rain_fall_mm_per_year,
            req.pesticides_tonnes, req.avg_temp
        ]], columns=[
            "Area", "Item", "Year",
            "average_rain_fall_mm_per_year",
            "pesticides_tonnes", "avg_temp"
        ])

        # Scale the features using the same scaler fitted during training
        scaled_features = artifacts.scaler.transform(df_features)

        # Run the prediction and round to 2 decimal places
        prediction = artifacts.model.predict(scaled_features)[0]
        return round(float(prediction), 2)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Prediction Endpoints ─────────────────────────────────────────────────────

@app.post("/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest, background_tasks: BackgroundTasks):
    """
    Main prediction endpoint.
    Accepts crop/environment data and returns the predicted yield.
    Also buffers the request for auto-retraining.
    """
    pred_val = _make_prediction(request)
    r2       = artifacts.metadata.get("r2_score", 0.0)

    # Add this prediction to the buffer for auto-retraining
    # We use the predicted value as the yield label since we don't
    # have the actual ground truth at prediction time
    new_data_buffer.append({
        "Area":                          request.area,
        "Item":                          request.item,
        "Year":                          request.year,
        "average_rain_fall_mm_per_year": request.average_rain_fall_mm_per_year,
        "pesticides_tonnes":             request.pesticides_tonnes,
        "avg_temp":                      request.avg_temp,
        "hg/ha_yield":                   pred_val
    })

    # Check if we've hit the threshold and should retrain
    auto_retrain_if_ready(background_tasks)

    return PredictionResponse(
        prediction=pred_val,
        predicted_yield_hg_per_ha=pred_val,
        area=request.area,
        item=request.item,
        year=request.year,
        model_type="Random Forest",
        model_r2_score=r2,
        timestamp=datetime.datetime.now().isoformat()
    )


class BatchPredictionRequest(BaseModel):
    """Wrapper for sending multiple predictions in one request."""
    predictions: List[PredictionRequest]


@app.post("/predict/batch", response_model=List[PredictionResponse])
def predict_batch(request: BatchPredictionRequest, background_tasks: BackgroundTasks):
    """
    Batch prediction endpoint — predict for multiple inputs at once.
    Useful for processing many rows without making individual API calls.
    All predictions in the batch are also buffered for auto-retraining.
    """
    r2        = artifacts.metadata.get("r2_score", 0.0)
    responses = []

    for p in request.predictions:
        pred_val = _make_prediction(p)

        # Buffer each prediction for auto-retrain
        new_data_buffer.append({
            "Area":                          p.area,
            "Item":                          p.item,
            "Year":                          p.year,
            "average_rain_fall_mm_per_year": p.average_rain_fall_mm_per_year,
            "pesticides_tonnes":             p.pesticides_tonnes,
            "avg_temp":                      p.avg_temp,
            "hg/ha_yield":                   pred_val
        })

        responses.append(PredictionResponse(
            prediction=pred_val,
            predicted_yield_hg_per_ha=pred_val,
            area=p.area, item=p.item, year=p.year,
            model_type="Random Forest",
            model_r2_score=r2,
            timestamp=datetime.datetime.now().isoformat()
        ))

    # Check auto-retrain after the whole batch is processed
    auto_retrain_if_ready(background_tasks)
    return responses


# ── Manual Retraining Endpoints ──────────────────────────────────────────────

@app.post("/retrain")
async def retrain(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    Manual retrain endpoint — upload a CSV file with new data.
    The CSV must have these columns:
    Area, Item, Year, average_rain_fall_mm_per_year,
    pesticides_tonnes, avg_temp, hg/ha_yield
    
    Retraining runs in the background so the response is immediate.
    """
    contents = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(contents))
        required = {"Area", "Item", "Year", "average_rain_fall_mm_per_year",
                    "pesticides_tonnes", "avg_temp", "hg/ha_yield"}
        if not required.issubset(set(df.columns)):
            raise HTTPException(
                status_code=400, detail="Missing required columns in CSV")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    background_tasks.add_task(do_retrain, contents)
    return {"message": "Retraining job started in the background"}


@app.post("/retrain/stream")
def retrain_stream(background_tasks: BackgroundTasks, data: List[dict]):
    """
    Stream-based retrain endpoint — send new data as a JSON list.
    This is useful for real-time pipelines where data arrives
    continuously and you want to retrain without uploading a file.
    """
    if not data:
        raise HTTPException(status_code=400, detail="Empty data list")

    required = {"Area", "Item", "Year", "average_rain_fall_mm_per_year",
                "pesticides_tonnes", "avg_temp", "hg/ha_yield"}
    if not required.issubset(set(data[0].keys())):
        raise HTTPException(
            status_code=400,
            detail=f"Missing required columns. Expected: {required}")
    try:
        df        = pd.DataFrame(data)
        csv_bytes = df.to_csv(index=False).encode("utf-8")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    background_tasks.add_task(do_retrain, csv_bytes)
    return {"message": "Retraining job from stream started in the background"}