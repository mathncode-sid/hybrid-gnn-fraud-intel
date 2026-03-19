# System Design Document: Graph-Based Fraud Intelligence System

## 1. System Requirements
**Functional Requirements:**
* [cite_start]Detect organized fraud rings and synthetic identities within the mobile money ecosystem[cite: 128].
* [cite_start]Utilize dynamic graph representations of transaction relationships to identify fraud patterns[cite: 130].
* [cite_start]Perform real-time continuous graph updates and inferences[cite: 73].
* [cite_start]Provide explainability for human analyst feedback using tools like GNNExplainer[cite: 253, 255].

**Non-Functional Requirements:**
* [cite_start]Evaluate performance using AUROC, F1-score, and False Positive Rates[cite: 40, 42, 260].
* [cite_start]Ensure temporal latency is minimized for real-time responsiveness[cite: 261].

## 2. System Modules
* [cite_start]**Data Ingestion/Streaming:** Manages the transaction stream using Kafka[cite: 250].
* [cite_start]**Graph Construction:** Represents users, agents, devices, and institutions as nodes[cite: 235]. [cite_start]Transactions, loan disbursements, and reversal requests act as edges[cite: 236].
* **Model Development (Hybrid-GNN):**
    * [cite_start]*GNN Component:* Learns structural topology[cite: 242].
    * [cite_start]*Temporal Component:* Detects fast-cash-out and burst fraud[cite: 245].
    * [cite_start]*Tabular Classifier:* Uses XGBoost on engineered features[cite: 246].
* [cite_start]**Backend:** FastAPI for logic, API services, and model inference[cite: 250].
* [cite_start]**Frontend:** React and Tailwind CSS for the user interface[cite: 250].

## 3. Technology Stack
* [cite_start]**Core/Modeling:** Python, PyTorch Geometric, Scikit-Learn, DGL[cite: 250].
* [cite_start]**Database/Storage:** Neo4j, GraphDB[cite: 250].
* [cite_start]**Infrastructure:** Kafka (Streaming), Docker (Deployment)[cite: 250].

## 4. Modeled Fraud Typologies (Case Studies)
[cite_start]The graph data pipeline is engineered to detect the following specific structural anomalies:
1. [cite_start]**Agent Reversal Scam Rings:** Modeled as a directed cycle followed by a fan-in pattern and a reversal request edge[cite: 197, 202].
2. [cite_start]**Mule Accounts & SIM Swap:** Modeled as star-shaped subgraphs where multiple synthetic accounts are linked to the same device[cite: 204, 206].
3. [cite_start]**Fast Cash-out Explosion:** Modeled as a high-velocity star topology occurring within a strictly small time window[cite: 208, 211].
4. [cite_start]**Synecdoche Circles (Loan Fraud):** Modeled as dense covert communities (homophily) where users borrow from institutions (like Fuliza/M-Shwari) and default together[cite: 213, 216, 217].
5. [cite_start]**Fraudulent Business Till Transactions:** Modeled as unusual densification and self-monitoring transaction circles between specific users and business tills[cite: 221, 223, 224].

## 5. System Architecture & Database Schema
*(Insert your architecture diagram image here)*



**Graph Database Schema (Entity-Relationship Diagram):**
```mermaid
erDiagram
    %% Nodes
    USER {
        string user_id PK
        int account_age_days
        string kyc_level
        boolean has_defaulted
    }
    AGENT {
        string agent_id PK
        string agent_type "Cash_Agent or Business_Till"
        string location
    }
    DEVICE {
        string device_id PK
        boolean is_rooted
    }
    INSTITUTION {
        string institution_id PK
        string name "e.g., Fuliza, M-Shwari"
    }

    %% Edges (Relationships)
    USER ||--o{ P2P_TRANSFER : initiates
    USER ||--o{ REVERSAL_REQUEST : disputes_transfer
    USER ||--o{ PAYMENT : pays_at_till
    USER ||--o{ WITHDRAWAL : cashes_out
    USER }o--|| DEVICE : uses
    INSTITUTION ||--o{ LOAN_DISBURSEMENT : issues_to

    week 3 work:
    # System Setup & Sync Guide (Windows Edition)

Follow these steps strictly in order to get your local environment fully up to speed with the Phase 3 Graph Neural Network pipeline.



## Step 1: Pull the Latest Code
Open your VS Code terminal and pull the latest pushed files:
```bash
git pull origin main

step 2: Activate your Virtual Environment
venv\Scripts\activate

step 3:Install Standard Dependancies
cd backend
pip install -r requirements.txt

step 4: Install Pytorch and Pytorch Geometric which i will say it is critical guys.

-Because deep learning libraries are massive, we must install them in a specific two-step process for Windows CPU.

run this as first: 
pip install torch torchvision torchaudio --index-url [https://download.pytorch.org/whl/cpu](https://download.pytorch.org/whl/cpu)

run this second:The graph Add-ons
pip install torch_geometric pyg_lib torch_scatter torch_sparse torch_cluster torch_spline_conv -f [https://data.pyg.org/whl/torch-2.3.0+cpu.html](https://data.pyg.org/whl/torch-2.3.0+cpu.html)


⚠️ WINDOWS ERROR WARNING: If the second command gives you a red error saying Could not find a version that satisfies the requirement pyg_lib, IGNORE IT. You successfully installed PyTorch Geometric! Those are optional C++ add-ons that we do not need for this project.

Step 5: Run the Complete Pipeline
Now that your environment is built, run these scripts in order to generate the data, push it to your local Neo4j database, and extract the PyTorch tensors.

1. Generate Data & Load to Neo4j:

python ml_pipeline/data_gen/generate_data.py

then

python ml_pipeline/graph_builder/neo4j_loader.py
 
 2. Run the Baseline ML Model (Watch it fail at complex fraud):

 python ml_pipeline/models/xgboost_classifier.py

 3. Extract the Graph Tensors for Deep Learning:

 python ml_pipeline/models/graph_dataset.py

 If the last script prints "Dataset successfully created and saved!", you are 100% at par and ready to train the Graph Neural Network NA MUWACHE KULALA CARO NA VICTOR!!
 

 Phase 1 of testing

 pull to the latest changes
 make sure your Neo4j DB is running and connected.
 pip -r install requiremnts.txt or just run pip install pytest
 then after that run:
 pytest tests/test_pipeline.py -v
 this to test for:
1. Data loader function
2.Feature extraction functions
3.Graph construction correctness 

