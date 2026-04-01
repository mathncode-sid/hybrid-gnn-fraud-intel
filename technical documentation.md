# Technical Documentation: Hybrid GNN Fraud Intelligence Journey

## 1. Goal and Thesis
- Build a real-time fraud detection pipeline for mobile money that combines graph learning with tabular classification.
- Prove the hypothesis: a hybrid model (GNN + XGBoost stack) improves detection on complex fraud topologies (fraud rings, synthetic identities, fast cashout) vs tabular-only baselines.
- Document the empirical journey using the three main model scripts: `evaluate_gnn.py`, `baseline_xgboost.py`, `stacked_hybrid.py`.

## 2. Repository layout (key folders)
- `streaming/`: Kafka producer (`transaction_producer.py`) and consumer (`graph_consumer.py`) for simulated transactions.
- `ml_pipeline/data_gen/`: data generator for synthetic datasets (`generate_data.py`).
- `ml_pipeline/features/` and `ml_pipeline/graph_builder/`: feature engineering and graph creation (not yet fully shipped in this snapshot).
- `ml_pipeline/models/`: core experiments:
  - `baseline_xgboost.py`: tabular-only baseline proof.
  - `evaluate_gnn.py`: GraphSAGE-based heterogeneous GNN evaluation.
  - `stacked_hybrid.py`: stacked hybrid model using GNN probabilities + tabular features.
- `backend/`: intended FastAPI serving, currently skeleton structure.
- `frontend/`: React dashboard components.
- `data/processed/`: expected serialized features/graphs for model training and evaluation.

## 3. `baseline_xgboost.py` (Statement of Proof)
- Loads `data/processed/final_model_data.csv`.
- Drops graph features (`triad_closure_score`, `pagerank_score`, `in_degree`, `out_degree`, `cycle_indicator`) to enforce tabular-only setting.
- Uses engineered features such as `transaction_frequency`, `num_unique_recipients`, `round_amount_flag`, `night_activity_flag`.
- Trains XGBoost with class-imbalance `scale_pos_weight` and evaluates recall per fraud scenario.
- Conclusion prints comparisons for `fraud_ring` vs `fast_cashout` (expected weakness of tabular baseline).

## 4. `evaluate_gnn.py` (Graph-Stage Model)
- Loads hetero-graph from `data/processed/hetero_graph.pt` (Node/edge attributes and train/test split rely on this artifact).
- Defines avoidable graph architecture:
  - `GNNEncoder` uses two `SAGEConv` layers, heterogenized by `to_hetero(...)`.
  - `EdgeClassifier` concatenates sender/receiver embeddings then classifies edge fraud with linear layers.
  - `HybridGNN` combines encoder + classifier.
- Uses an 80/20 random edge split (seed 42), balancing via pos_weight = neg / pos.
- Trains 100 epochs with `BCEWithLogitsLoss` on train edges.
- Evaluates with ROC-AUC and `classification_report`.
- Adds scenario-based blind-spot analysis via `data/processed/final_model_data.csv` and per-scenario recall for >1 fraud scenarios.

## 5. `stacked_hybrid.py` (Feature Stacking and Business Logic)
- Reads original tabular `final_model_data.csv` and GNN outputs `gnn_probabilities.csv`.
- Concatenates (`pd.concat`) to create `hybrid_df` with stacked GNN probability as additional feature.
- Trains XGBoost with tuned hyperparameters:
  - n_estimators=150, max_depth=4, learning_rate=0.05, colsample_bytree=0.6.
  - scale_pos_weight=pos_weight * 1.5 to intentionally upweight fraud.
- Performs stratified 80/20 split.
- Evaluates per scenario and overall (ROC AUC, classification report).
- Adds human-in-the-loop decision rule:
  - `>=0.85 -> AUTO_FREEZE`, `>=0.25 -> MANUAL_REVIEW`, else `SAFE`.
- Exports `review_queue.csv` for tier-2 AI analyst queue.

## 6. End-to-end analysis narrative (your argument)
1. Baseline XGBoost demonstrates performance without graph context and shows blind spots on graph-based fraud topology.
2. GNN model recovers latent connectedness; evaluate using balanced edge classification and scenario recall.
3. Stacked hybrid injects GNN signal to XGBoost, bridging structural topology with classic features.
4. Human-in-the-loop business logic gives practical KPI translation: precision-vs-recall and analyst workload.
5. Suite of scripts proves claim: hybrid outperforms pure tabular on complex fraud rings, while preserving operational safety.

## 7. How to run (as found in code styling)
```powershell
cd D:\hybrid-gnn-fraud-intel
python ml_pipeline/models/baseline_xgboost.py
python ml_pipeline/models/evaluate_gnn.py
python ml_pipeline/models/stacked_hybrid.py
```
- Ensure `data/processed/final_model_data.csv` is generated and `hetero_graph.pt` exists.
- If using Docker/Kafka/Neo4j, start with `docker-compose up` (stack includes streaming, db, backend, frontend when available).

## 8. Suggested next updates to strengthen documentation
- Add explicit `data/processed` generation step from `ml_pipeline/data_gen/generate_data.py`.
- Document expected columns in `final_model_data.csv` and `gnn_probabilities.csv`.
- Add sample output of scenario recall table in markdown for reference.
- Add API endpoint mapping when `backend` is implemented (likely under `backend/api/`).

---
*File generated in root: `technical documentation.md`*