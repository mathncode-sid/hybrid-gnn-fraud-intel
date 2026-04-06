from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from neo4j import GraphDatabase
import pandas as pd
import xgboost as xgb
import pickle
import os
import sqlite3
from datetime import datetime

# 1. INITIALIZE APP & CONNECTIONS 
app = FastAPI(title="M-Pesa Fraud Intelligence API", version="1.0")

# CORS MIDDLEWARE BLOCK 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Neo4j Connection (Update with your local credentials)
URI = "neo4j://localhost:7687"
AUTH = ("neo4j", "12345678")
driver = GraphDatabase.driver(URI, auth=AUTH)

# Load the trained Hybrid Meta-Learner (Tier 1)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "models", "saved", "hybrid_xgboost.pkl")

try:
    with open(MODEL_PATH, "rb") as f:
        hybrid_model = pickle.load(f)
    print(f"✅ SUCCESS: AI Brain loaded from {MODEL_PATH}")
except FileNotFoundError:
    print(f"Warning: Model file not found at {MODEL_PATH}. API will fail on prediction.")


# --- NEW: SQLITE DATABASE INITIALIZATION ---
def init_db():
    """Creates a local SQLite database to store transactions for the dashboard."""
    conn = sqlite3.connect("fraud_intel.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id TEXT,
            timestamp DATETIME,
            sender_id TEXT,
            receiver_id TEXT,
            amount REAL,
            risk_score REAL,
            decision TEXT,
            reason TEXT
        )
    """)
    conn.commit()
    conn.close()

# Run database setup immediately when server starts
init_db()


# 2. DEFINE DATA SCHEMAS (Pydantic) 
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
    decision: str 
    reason: str

# 3. THE AI ANALYST BUSINESS LOGIC (Tier 2) 
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

# 4. API ENDPOINTS 

@app.post("/predict", response_model=PredictionResponse)
async def predict_fraud(tx: TransactionRequest):
    """
    The Core Engine: 
    1. Receives tabular data. 
    2. Queries Neo4j for network context and updates the graph. 
    3. Runs Hybrid Model. 
    4. Applies AI Analyst rules.
    """
    # 1. LIVE GRAPH UPDATE: Add the new transaction, then count the connections
    cypher_query = """
    // Ensure both users exist in the graph
    MERGE (s:User {user_id: $sender_id})
    MERGE (r:User {user_id: $receiver_id})
    
    // Draw the new transaction line (The Graph Update)
    MERGE (s)-[tx:SENT_MONEY {transaction_id: $tx_id}]->(r)
    SET tx.amount = toFloat($amount)
    
    // Calculate the updated network topology for the model
    WITH s
    MATCH (s)-[:SENT_MONEY]->(u:User)
    RETURN count(DISTINCT u) AS num_unique_recipients
    """
    
    try:
        with driver.session() as session:
            result = session.run(
                cypher_query, 
                sender_id=tx.sender_id,
                receiver_id=tx.receiver_id,
                tx_id=tx.transaction_id,
                amount=tx.amount
            )
            record = result.single()
            num_unique_recipients = record["num_unique_recipients"] if record else 0
            
            mock_gnn_score = 0.45 
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Neo4j Database Error: {str(e)}")

    # 2. Build the exact feature row our XGBoost model expects
    features = pd.DataFrame([{
        "amount": tx.amount,
        "num_accounts_linked": 1,                      
        "shared_device_flag": 0,                       
        "avg_transaction_amount": 1500.0,              
        "transaction_frequency": 2,                    
        "num_unique_recipients": num_unique_recipients,
        "transactions_last_24hr": tx.transactions_last_24hr, 
        "round_amount_flag": 1 if tx.amount % 100 == 0 else 0, 
        "hour": tx.hour,                               
        "night_activity_flag": 1 if tx.hour < 5 else 0,
        "triad_closure_score": 0.1,                    
        "pagerank_score": 0.005,                       
        "in_degree": 2,                                
        "out_degree": num_unique_recipients,           
        "cycle_indicator": 0,                          
        "gnn_fraud_risk_score": mock_gnn_score         
    }])

    # 3. Model Inference
    try:
        risk_score = hybrid_model.predict_proba(features)[0][1]
        print(f"✅ XGBoost Calculation Success! Real Risk Score: {risk_score}")
    except Exception as e:
         print(f"❌ XGBoost Feature Mismatch Error: {str(e)}") 
         risk_score = 0.65 

    # 4. Tier 2 AI Analyst Decision
    decision, reason = apply_ai_analyst(tx.amount, tx.transactions_last_24hr, risk_score)
    final_score_percentage = round(risk_score * 100, 1)

    #  NEW: SAVE TO SQLITE DATABASE
    conn = sqlite3.connect("fraud_intel.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO transactions (transaction_id, timestamp, sender_id, receiver_id, amount, risk_score, decision, reason)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (tx.transaction_id, datetime.now(), tx.sender_id, tx.receiver_id, tx.amount, final_score_percentage, decision, reason))
    conn.commit()
    conn.close()

    return PredictionResponse(
        transaction_id=tx.transaction_id,
        risk_score=round(risk_score, 4),
        decision=decision,
        reason=reason
    )

#  DASHBOARD DATA ENDPOINT 
@app.get("/dashboard-stats")
async def get_dashboard_stats():
    """Endpoint for the Home dashboard to fetch real-time SQLite metrics."""
    conn = sqlite3.connect("fraud_intel.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get totals
    cursor.execute("SELECT COUNT(*) FROM transactions")
    total_tx = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM transactions WHERE decision != 'AUTO_CLEARED_SAFE'")
    fraud_tx = cursor.fetchone()[0]

    # Get risk distribution for pie chart
    cursor.execute("SELECT COUNT(*) FROM transactions WHERE decision = 'AUTO_CLEARED_SAFE'")
    low_risk = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM transactions WHERE decision = 'REQUIRE_HUMAN'")
    medium_risk = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM transactions WHERE decision = 'CONFIRMED_FRAUD' OR decision = 'AUTO_FREEZE'")
    high_risk = cursor.fetchone()[0]

    # Get recent alerts (only suspicious ones)
    cursor.execute("""
        SELECT transaction_id, sender_id, receiver_id, amount, risk_score, decision 
        FROM transactions WHERE decision != 'AUTO_CLEARED_SAFE' 
        ORDER BY timestamp DESC LIMIT 4
    """)
    recent_rows = cursor.fetchall()
    
    recent_alerts = []
    for r in recent_rows:
        recent_alerts.append({
            "id": r["transaction_id"],
            "time": "Just now", 
            "sender": r["sender_id"],
            "receiver": r["receiver_id"],
            "amount": f"Ksh {r['amount']}",
            "score": r["risk_score"],
            "status": "High" if "FRAUD" in r["decision"] or "FREEZE" in r["decision"] else "Medium"
        })

    conn.close()

    return {
        "kpis": {
            "total": total_tx,
            "fraud": fraud_tx,
            "rate": round((fraud_tx / total_tx * 100), 1) if total_tx > 0 else 0
        },
        "pie": [
            {"name": "Low Risk", "value": low_risk if low_risk > 0 else 1, "color": "#10b981"},
            {"name": "Medium Risk", "value": medium_risk if medium_risk > 0 else 1, "color": "#f59e0b"},
            {"name": "High Risk", "value": high_risk if high_risk > 0 else 1, "color": "#ef4444"}
        ],
        "alerts": recent_alerts
    }