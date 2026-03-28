import pandas as pd
import numpy as np
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score

print(" Group 15: STACKED HYBRID GNN-XGBoost Evaluation ")

# 1. Load the Data
print("Loading Tabular features...")
df = pd.read_csv('data/processed/final_model_data.csv')

print("Loading GNN Probabilities (The Stacked Feature)...")
probs_df = pd.read_csv('data/processed/gnn_probabilities.csv')

# 2. STACKING: Because the PyTorch graph edges perfectly match the CSV rows, 
# we can just glue the probability column directly to the dataframe.
hybrid_df = pd.concat([df, probs_df], axis=1)

# 3. Prepare for Machine Learning
drop_cols = ['sender_id', 'receiver_id', 'timestamp', 'device_id', 'agent_id', 
             'is_fraud', 'fraud_scenario']
X = hybrid_df.drop(columns=drop_cols, errors='ignore')
y = hybrid_df['is_fraud']
scenarios = hybrid_df['fraud_scenario']

# 4. Split Data (Strict 42 Seed)
X_train, X_test, y_train, y_test, scen_train, scen_test = train_test_split(
    X, y, scenarios, test_size=0.2, random_state=42, stratify=y
)

# 5. Train the Stacked XGBoost
print(f"Training STACKED XGBoost on {len(X_train)} transactions...")
pos_weight = (len(y_train) - sum(y_train)) / sum(y_train)

stacked_model = XGBClassifier(
    n_estimators=100, 
    max_depth=6, 
    learning_rate=0.1, 
    scale_pos_weight=pos_weight, 
    random_state=42,
    eval_metric='logloss'
)
stacked_model.fit(X_train, y_train)

# 6. Evaluation
print("\n STACKED Model Detection Analysis ")
predictions = stacked_model.predict(X_test)
probabilities = stacked_model.predict_proba(X_test)[:, 1]

results = pd.DataFrame({
    'Actual': y_test,
    'Predicted': predictions,
    'Scenario': scen_test
})

actual_fraud = results[results['Actual'] == 1]

print(f"{'Fraud Topology':<20} | {'Caught (True Pos)'} | {'Missed (False Neg)'} | {'Recall (Detection Rate)'}")
print("-" * 75)

for scenario in actual_fraud['Scenario'].unique():
    scenario_data = actual_fraud[actual_fraud['Scenario'] == scenario]
    total_cases = len(scenario_data)
    caught = sum(scenario_data['Predicted'] == 1)
    missed = total_cases - caught
    recall = (caught / total_cases) * 100 if total_cases > 0 else 0.0
    print(f"{scenario:<20} | {caught:<17} | {missed:<18} | {recall:.1f}%")

print("\n--- Overall Performance ---")
print(classification_report(y_test, predictions, target_names=['Safe (0)', 'Fraud (1)']))
print(f"STACKED ROC-AUC Score: {roc_auc_score(y_test, probabilities):.4f}")