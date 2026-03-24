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

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://crop-yield-predictor-api-nhma.onrender.com",
        "http://localhost",
        "http://localhost:8080",
        "http://127.0.0.1",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

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

# Lookup maps for case-insensitive matching
_AREA_MAP = {a.lower(): a for a in VALID_AREAS}
_CROP_MAP = {c.lower(): c for c in VALID_CROPS}

ARTIFACTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "linear_regression")

class ModelArtifacts:
    model: Optional[RandomForestRegressor] = None
    scaler: Optional[StandardScaler] = None
    le_area: Optional[LabelEncoder] = None
    le_item: Optional[LabelEncoder] = None
    metadata: dict = {}

artifacts = ModelArtifacts()

def load_artifacts():
    try:
        artifacts.model = joblib.load(os.path.join(ARTIFACTS_DIR, "best_model.pkl"))
        artifacts.scaler = joblib.load(os.path.join(ARTIFACTS_DIR, "scaler.pkl"))

        # Load from combined label_encoders.pkl
        label_encoders = joblib.load(os.path.join(ARTIFACTS_DIR, "label_encoders.pkl"))
        artifacts.le_area = label_encoders['Area']
        artifacts.le_item = label_encoders['Item']

        with open(os.path.join(ARTIFACTS_DIR, "model_metadata.json"), "r") as f:
            artifacts.metadata = json.load(f)
        print(" Model artifacts loaded successfully.")
    except Exception as e:
        print(f"Warning: Failed to load some artifacts: {e}")

@app.on_event("startup")
def startup_event():
    load_artifacts()


class PredictionRequest(BaseModel):
    area: str
    item: str
    year: int = Field(..., ge=1990, le=2030)
    average_rain_fall_mm_per_year: float = Field(..., ge=51.0, le=3240.0)
    pesticides_tonnes: float = Field(..., ge=0.0, le=400000.0)
    avg_temp: float = Field(..., ge=1.3, le=30.65)

    @validator('area')
    def validate_area(cls, v):
        if v in VALID_AREAS:
            return v
        normalized = _AREA_MAP.get(v.lower())
        if normalized:
            return normalized
        raise ValueError(
            f"Unknown country: '{v}'. "
            f"See the /areas endpoint for all {len(VALID_AREAS)} supported countries."
        )

    @validator('item')
    def validate_item(cls, v):
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
    predicted_yield_hg_per_ha: float
    area: str
    item: str
    year: int
    model_type: str
    model_r2_score: float
    timestamp: str

@app.get("/")
def read_root():
    return {
        "message": "Welcome to the Crop Yield Predictor API",
        "docs": "/docs"
    }

@app.get("/health")
def health_check():
    status = "healthy" if artifacts.model is not None else "model_missing"
    return {
        "status": status,
        "r2_score": artifacts.metadata.get("r2_score"),
        "rmse": artifacts.metadata.get("rmse"),
        "valid_crops": VALID_CROPS,
        "timestamp": datetime.datetime.now().isoformat()
    }

@app.get("/areas")
def get_areas():
    return VALID_AREAS

@app.get("/crops")
def get_crops():
    return VALID_CROPS

def _make_prediction(req: PredictionRequest) -> float:
    if not artifacts.model:
        raise HTTPException(status_code=500, detail="Models are not loaded.")
    try:
        area_enc = artifacts.le_area.transform([req.area])[0]
        item_enc = artifacts.le_item.transform([req.item])[0]
        
        df_features = pd.DataFrame([[
            area_enc,
            item_enc,
            req.year,
            req.average_rain_fall_mm_per_year,
            req.pesticides_tonnes,
            req.avg_temp
        ]], columns=[
            "Area", "Item", "Year", "average_rain_fall_mm_per_year",
            "pesticides_tonnes", "avg_temp"
        ])
        
        scaled_features = artifacts.scaler.transform(df_features)
        prediction = artifacts.model.predict(scaled_features)[0]
        return round(float(prediction), 2)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest):
    pred_val = _make_prediction(request)
    r2 = artifacts.metadata.get("r2_score", 0.0) if artifacts.metadata else 0.0
    return PredictionResponse(
        predicted_yield_hg_per_ha=pred_val,
        area=request.area,
        item=request.item,
        year=request.year,
        model_type="Random Forest",
        model_r2_score=r2,
        timestamp=datetime.datetime.now().isoformat()
    )

class BatchPredictionRequest(BaseModel):
    predictions: List[PredictionRequest]

@app.post("/predict/batch", response_model=List[PredictionResponse])
def predict_batch(request: BatchPredictionRequest):
    r2 = artifacts.metadata.get("r2_score", 0.0) if artifacts.metadata else 0.0
    responses = []
    for p in request.predictions:
        pred_val = _make_prediction(p)
        responses.append(PredictionResponse(
            predicted_yield_hg_per_ha=pred_val,
            area=p.area,
            item=p.item,
            year=p.year,
            model_type="Random Forest",
            model_r2_score=r2,
            timestamp=datetime.datetime.now().isoformat()
        ))
    return responses

def do_retrain(csv_content: bytes):
    try:
        df_new = pd.read_csv(io.BytesIO(csv_content))
        orig_csv_path = os.path.join(ARTIFACTS_DIR, "yield_df.csv")
        if os.path.exists(orig_csv_path):
            df_orig = pd.read_csv(orig_csv_path)
            df_combined = pd.concat([df_orig, df_new], ignore_index=True)
        else:
            df_combined = df_new

        le_area = LabelEncoder()
        df_combined['Area'] = le_area.fit_transform(df_combined['Area'])

        le_item = LabelEncoder()
        df_combined['Item'] = le_item.fit_transform(df_combined['Item'])

        X = df_combined[['Area', 'Item', 'Year', 'average_rain_fall_mm_per_year', 'pesticides_tonnes', 'avg_temp']]
        y = df_combined['hg/ha_yield']

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)

        model = RandomForestRegressor(n_estimators=50, max_depth=10, random_state=42, n_jobs=-1)
        model.fit(X_train, y_train)

        preds = model.predict(X_test)
        new_r2 = float(r2_score(y_test, preds))
        new_rmse = float(mean_squared_error(y_test, preds, squared=False))

        os.makedirs(ARTIFACTS_DIR, exist_ok=True)
        joblib.dump(model, os.path.join(ARTIFACTS_DIR, "best_model.pkl"))
        joblib.dump(scaler, os.path.join(ARTIFACTS_DIR, "scaler.pkl"))

        # Save as combined label_encoders.pkl
        joblib.dump({'Area': le_area, 'Item': le_item}, os.path.join(ARTIFACTS_DIR, "label_encoders.pkl"))

        meta = {"r2_score": new_r2, "rmse": new_rmse, "retrained_at": datetime.datetime.now().isoformat()}
        with open(os.path.join(ARTIFACTS_DIR, "model_metadata.json"), "w") as f:
            json.dump(meta, f)

        df_combined.to_csv(os.path.join(ARTIFACTS_DIR, "yield_df.csv"), index=False)

        artifacts.model = model
        artifacts.scaler = scaler
        artifacts.le_area = le_area
        artifacts.le_item = le_item
        artifacts.metadata = meta
        print(" Retraining completed successfully.")
    except Exception as e:
        print(f"Retraining failed: {e}")

@app.post("/retrain")
async def retrain(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    contents = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(contents))
        required = {"Area", "Item", "Year", "average_rain_fall_mm_per_year", "pesticides_tonnes", "avg_temp", "hg/ha_yield"}
        if not required.issubset(set(df.columns)):
            raise HTTPException(status_code=400, detail="Missing required columns in CSV")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    background_tasks.add_task(do_retrain, contents)
    return {"message": "Retraining job started in the background"}

@app.post("/retrain/stream")
def retrain_stream(background_tasks: BackgroundTasks, data: List[dict]):
    if not data:
        raise HTTPException(status_code=400, detail="Empty data list")
    required = {"Area", "Item", "Year", "average_rain_fall_mm_per_year", "pesticides_tonnes", "avg_temp", "hg/ha_yield"}
    if not required.issubset(set(data[0].keys())):
        raise HTTPException(status_code=400, detail=f"Missing required columns. Expected: {required}")
    try:
        df = pd.DataFrame(data)
        csv_bytes = df.to_csv(index=False).encode('utf-8')
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    background_tasks.add_task(do_retrain, csv_bytes)
    return {"message": "Retraining job from stream started in the background"}