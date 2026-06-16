import pandas as pd
import joblib
from pipeline.preprocess import preprocess

model = joblib.load("Model Processing/attack_detector.pkl")
feature_cols = joblib.load("Model Processing/feature_columns.pkl")

def predict(log_dict) :
    df = pd.DataFrame([log_dict])

    #Preprocessing the logs
    df = preprocess(df)

    for col in feature_cols :
        if col not in df.columns :
            df[col] = 0
    
    df = df[feature_cols]
    print("DEBUG INPUT TO MODEL:\n", df)

    #Making predictions
    pred = model.predict(df)[0]
    prob = model.predict_proba(df)[0][1]
    print("DEBUG PROB:", prob)

    return {
    "Prediction": "ATTACK" if pred == 1 else "NORMAL",
    "Confidence": float(prob),
    "Risk": "HIGH" if pred == 1 else "LOW"
}
