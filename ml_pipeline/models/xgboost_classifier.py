import pandas as pd
from neo4j import GraphDatabase
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score, confusion_matrix
from sklearn.preprocessing import LabelEncoder

# 1. Database Connection
URI = "neo4j://localhost:7687"
AUTH = ("neo4j", "12345678") # Update to match your password!

def extract_tabular_data():
    print("Extracting flat tabular data from Neo4j...")
    driver = GraphDatabase.driver(URI, auth=AUTH)
    
    # We pull transaction details and basic sender attributes (no graph structure)
    query = """
    MATCH (s:User)-[t]->(r)
    WHERE type(t) IN ['P2P_TRANSFER', 'WITHDRAWAL', 'PAYMENT', 'LOAN_DISBURSEMENT', 'REVERSAL_REQUEST']
    RETURN 
        t.amount AS amount,
        type(t) AS tx_type,
        s.account_age_days AS sender_age,
        s.kyc_level AS sender_kyc,
        s.has_defaulted AS sender_defaulted,
        t.is_fraud AS label,
        t.fraud_scenario AS scenario
    """
    
    with driver.session() as session:
        result = session.run(query)
        data = [record.data() for record in result]
        
    driver.close()
    return pd.DataFrame(data)

def train_and_evaluate():
    df = extract_tabular_data()
    print(f"Extracted {len(df)} transactions.")
    
    # 2. Preprocessing (Encoding categorical text into numbers for XGBoost)
    le_tx = LabelEncoder()
    le_kyc = LabelEncoder()
    
    df['tx_type_encoded'] = le_tx.fit_transform(df['tx_type'])
    # Handle potentially missing KYC levels (e.g., if a lender institution is the sender)
    df['sender_kyc'] = df['sender_kyc'].fillna('Unknown')
    df['sender_kyc_encoded'] = le_kyc.fit_transform(df['sender_kyc'])
    
    # Fill any null numerical values
    df['sender_age'] = df['sender_age'].fillna(df['sender_age'].median())
    df['sender_defaulted'] = df['sender_defaulted'].fillna(0)

    # Define our features (X) and our target label (y)
    features = [ 'tx_type_encoded', 'sender_age', 'sender_kyc_encoded']
    X = df[features]
    y = df['label']
    
    # Split into Training (80%) and Testing (20%)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    print("\nTraining XGBoost Baseline Model...")
    model = xgb.XGBClassifier(
        n_estimators=100,
        learning_rate=0.1,
        max_depth=5,
        scale_pos_weight=10, # Helps with imbalanced fraud data
        random_state=42
    )
    model.fit(X_train, y_train)
    
    # 3. Overall Evaluation
    print("\n OVERALL MODEL PERFORMANCE ")
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]
    
    print(classification_report(y_test, y_pred))
    print(f"ROC-AUC Score: {roc_auc_score(y_test, y_prob):.4f}")
    print("Confusion Matrix:")
    print(confusion_matrix(y_test, y_pred))
    
    # 4. Our Reaseach Proposal Proof: Evaluation by Fraud Scenario
    print("\n PERFORMANCE BY FRAUD SCENARIO (The Research Proposal Proof) ")
    test_indices = X_test.index
    test_df = df.iloc[test_indices].copy()
    test_df['predicted_fraud'] = y_pred
    
    scenarios = test_df['scenario'].unique()
    for scenario in scenarios:
        if scenario == 'Normal': continue
        
        scenario_data = test_df[test_df['scenario'] == scenario]
        total_cases = len(scenario_data)
        if total_cases == 0: continue
            
        caught = scenario_data['predicted_fraud'].sum()
        missed = total_cases - caught
        detection_rate = (caught / total_cases) * 100
        
        print(f"Scenario: {scenario}")
        print(f"  Total instances in test set: {total_cases}")
        print(f"  Caught: {caught} | Missed: {missed}")
        print(f"  Detection Rate: {detection_rate:.2f}%")
        if detection_rate < 50:
            print("  -> STATUS: XGBoost STRUGGLES to detect this topological pattern.")
        print("-" * 40)

if __name__ == "__main__":
    train_and_evaluate()