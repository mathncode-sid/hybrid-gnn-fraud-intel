from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from neo4j import GraphDatabase
import pandas as pd
import xgboost as xgb
import pickle # Assuming you saved your XGBoost model as a .pkl file
import os # <-- Added to fix the pathing issue

#  1. INITIALIZE APP & CONNECTIONS 
app = FastAPI(title="M-Pesa Fraud Intelligence API", version="1.0")

# Neo4j Connection (Update with your local credentials)
URI = "neo4j://localhost:7687"
AUTH = ("neo4j", "12345678")
driver = GraphDatabase.driver(URI, auth=AUTH)

# Load the trained Hybrid Meta-Learner (Tier 1)
# Dynamically find the absolute path to your main project folder
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Based on your script output, it saved to 'models/saved/hybrid_xgboost.pkl'
MODEL_PATH = os.path.join(BASE_DIR, "models", "saved", "hybrid_xgboost.pkl")

try:
    with open(MODEL_PATH, "rb") as f:
        hybrid_model = pickle.load(f)
    print(f"✅ SUCCESS: AI Brain loaded from {MODEL_PATH}")
except FileNotFoundError:
    print(f"Warning: Model file not found at {MODEL_PATH}. API will fail on prediction.")


#  2. DEFINE DATA SCHEMAS (Pydantic) 
# This forces the incoming API requests to have exactly these fields
class TransactionRequest(BaseModel):
    transaction_id: str
    sender_id: str
    receiver_id: str
    amount: float
    transactions_last_24hr: int
    hour: int

class PredictionResponse(BaseModel):
    transaction_id: str
    risk_score: float
    decision: str # AUTO_FREEZE, REQUIRE_HUMAN, AUTO_CLEARED_SAFE
    reason: str

#  3. THE AI ANALYST BUSINESS LOGIC (Tier 2) 
def apply_ai_analyst(amount: float, velocity: int, risk_score: float) -> tuple[str, str]:
    """Applies the Kenyan M-Pesa rules to the Hybrid model's risk score."""
    if risk_score >= 0.85:
        return "AUTO_FREEZE", "High confidence of severe fraud topology."
    
    # The queue rules (0.25 to 0.84)
    if risk_score > 0.50 and amount < 300 and velocity > 5:
        return "CONFIRMED_FRAUD", "Micro-scam velocity detected (Kamiti rule)."
    elif risk_score < 0.50 and 100 <= amount <= 3000 and velocity < 4:
        return "AUTO_CLEARED_SAFE", "Normal retail behavior (Kiosk rule)."
    elif amount > 100000:
        return "REQUIRE_HUMAN", "High-value compliance limit exceeded (Wash-Wash rule)."
    else:
        return "REQUIRE_HUMAN", "Ambiguous pattern. Manual review required."

#  4. API ENDPOINTS 

@app.post("/predict", response_model=PredictionResponse)
async def predict_fraud(tx: TransactionRequest):
    """
    The Core Engine: 
    1. Receives tabular data. 
    2. Queries Neo4j for network context. 
    3. Runs Hybrid Model. 
    4. Applies AI Analyst rules.
    """
    # 1. Fetch live network features from Neo4j
    # We ask the graph: "How many suspicious connections does this sender have right now?"
    cypher_query = """
    MATCH (s:User {user_id: $sender_id})-[r:SENT_MONEY]->(u:User)
    RETURN count(DISTINCT u) AS num_unique_recipients
    """
    
    try:
        with driver.session() as session:
            result = session.run(cypher_query, sender_id=tx.sender_id)
            record = result.single()
            num_unique_recipients = record["num_unique_recipients"] if record else 0
            
            # (In a real system, I would also fetch THE GNN score or PageRank here)
            # For this example, we will mock the GNN score
            mock_gnn_score = 0.45 
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Neo4j Database Error: {str(e)}")

    # 2. Build the exact feature row your XGBoost model expects
    features = pd.DataFrame([{
        "amount": tx.amount,
        "transactions_last_24hr": tx.transactions_last_24hr,
        "hour": tx.hour,
        "num_unique_recipients": num_unique_recipients,
        "gnn_fraud_risk_score": mock_gnn_score 
        # Add the rest of your 10 features here...
    }])

    # 3. Model Inference
    try:
        risk_score = hybrid_model.predict_proba(features)[0][1]
    except Exception as e:
         # Fallback if model isn't loaded properly for this demo
         risk_score = 0.65 

    # 4. Tier 2 AI Analyst Decision
    decision, reason = apply_ai_analyst(tx.amount, tx.transactions_last_24hr, risk_score)

    return PredictionResponse(
        transaction_id=tx.transaction_id,
        risk_score=round(risk_score, 4),
        decision=decision,
        reason=reason
    )

@app.get("/alert")
async def get_alerts():
    """Endpoint for the front-end dashboard to fetch the Review Queue."""
    # In reality, I would query a database table where I save "REQUIRE_HUMAN" tickets.
    return {
        "status": "success",
        "active_alerts": 142,
        "message": "Fetch from the database queue here."
    }