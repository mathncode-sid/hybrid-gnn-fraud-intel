# System Design Document: Graph-Based Fraud Intelligence System

## 1. System Requirements
**Functional Requirements:**
* [span_0](start_span)Detect fraud rings and synthetic identities within the mobile money ecosystem[span_0](end_span).
* [span_1](start_span)Utilize dynamic graph representations of transaction relationships to identify fraud patterns[span_1](end_span).
* [span_2](start_span)Perform real-time continuous graph updates and inferences[span_2](end_span).
* [span_3](start_span)[span_4](start_span)Provide explainability for human analyst feedback using tools like GNNExplainer[span_3](end_span)[span_4](end_span).

**Non-Functional Requirements:**
* [span_5](start_span)[span_6](start_span)Evaluate performance using AUROC, F1-score, and False Positive Rates[span_5](end_span)[span_6](end_span).
* [span_7](start_span)Ensure temporal latency is minimized for real-time responsiveness[span_7](end_span).

## 2. System Modules
* **[span_8](start_span)Data Ingestion/Streaming:** Manages the transaction stream using Kafka[span_8](end_span).
* **[span_9](start_span)[span_10](start_span)Graph Construction:** Represents users, agents, and devices as nodes, and transactions as edges[span_9](end_span)[span_10](end_span).
* **Model Development (Hybrid-GNN):**
    * *[span_11](start_span)GNN Component:* Learns structural topology[span_11](end_span).
    * *[span_12](start_span)Temporal Component:* Detects fast-cash-out and burst fraud[span_12](end_span).
    * *[span_13](start_span)Tabular Classifier:* Uses XGBoost on engineered features[span_13](end_span).
* **[span_14](start_span)Backend:** FastAPI for logic, API services, and model inference[span_14](end_span).
* **[span_15](start_span)Frontend:** React and Tailwind CSS for the user interface[span_15](end_span).

## 3. Technology Stack
* **[span_16](start_span)Core/Modeling:** Python, PyTorch Geometric, Scikit-Learn, DGL[span_16](end_span).
* **[span_17](start_span)Database/Storage:** Neo4j, GraphDB[span_17](end_span).
* **[span_18](start_span)Infrastructure:** Kafka (Streaming), Docker (Deployment)[span_18](end_span).
*

## System Modules

* [cite_start]**Data Ingestion Module**: Handles the streaming of real-time transaction data and simulation using Kafka[cite: 250]. This module acts as the entry point for all mobile money traffic.
* [cite_start]**Graph Construction Module**: Responsible for transforming the data stream into a dynamic, non-homogenous graph stored in Neo4j[cite: 234, 250]. 
  * [cite_start]**Nodes**: Represents entities like devices, simulated agents, and users (synthetic customers)[cite: 235].
  * [cite_start]**Edges**: Represents real transaction flows such as P2P transfers, payments, and withdrawals[cite: 236].
* [cite_start]**GNN Model Module**: Utilizes PyTorch Geometric to learn structural embeddings representing the topology of relational interactions between transactions[cite: 242, 250]. [cite_start]It also incorporates time-sensitive layers to detect burst fraud and fast cash-outs[cite: 245].
* [cite_start]**ML Classifier Module**: An XGBoost (gradient-boosted tree) tabular classifier trained on engineered features (e.g., transaction velocity)[cite: 246]. [cite_start]It combines its outputs with the deep graph embeddings to compute the final fraud risk score[cite: 247].
* [cite_start]**API Backend**: Built with FastAPI to handle the core logic, API services, and real-time model inference[cite: 250].
* [cite_start]**Frontend Dashboard**: A user interface developed using React and Tailwind CSS to display the alert manager, visualize fraud rings, and present actionable insights to analysts[cite: 250].