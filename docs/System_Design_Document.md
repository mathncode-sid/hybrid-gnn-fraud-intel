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

Now that we have the automated testing working, we need to run the manual tests to  confirm if it makes sense
Open Neo4j and run this query:
    MATCH p=(u1:User)-[r:LOAN_DISBURSEMENT]->(u2:User) WHERE r.is_fraud = 1 RETURN p LIMIT 50
So the Manual check is : Does it actually form a circle? Are there dense connections? If it just looks like a straight line, your data generator logic has a flaw that pytest couldn't catch

Second Test is the Tensor Sanity check. Open a Python Interactive Terminal (jupyter notebook) and look at the raw numbers. Run this code
    import torch
    data = torch.load('data/processed/hetero_graph.pt')
 
    # Look at the first 5 users' features
print(data['user'].x[:5])
 
    # Look at the transaction amounts for the first 5 P2P transfers
    print(data['user', 'p2p', 'user'].edge_attr[:5])
Manual check will be: Are the numbers mostly between -3 and 3 (normalized)? If you see numbers like 99999 or NaN, then our feature engineering has a bug.

Third test will be the Edge Case Hunting(Finding impossible scenarios in the Neo4j database)
1. Visualizing our topology
Run this command in ne04j query:
    MATCH p=(u1:User)-[r:P2P_TRANSFER]->(u2:User) WHERE r.is_fraud = 1 RETURN p LIMIT 50
This should be visualizing the Fraudulent P2P rings. You should see a dense network of fraudsters sending money to each other.(Actual complex topology XGBoost missed)

2. Visualizing Fraudulent Loans
If you specifically want to see the bad loans being handed out to these fraudsters, we have to start the edge at an Institution node, not a User node. Run this command:
    MATCH p=(i:Institution)-[r:LOAN_DISBURSEMENT]->(u:User) WHERE r.is_fraud = 1 RETURN p LIMIT 50

The Star Topology: One central node with 10+ nodes pointing perfectly inward or outward (This is the Mule SIM Swap / Fast Cashout).
The Dense Clusters: A tight web of nodes all aggressively transacting with each other (This is the Synecdoche Circle / Layering topology).
So this is what pur proposal  clarification.The XGBoost model we trained earlier couldn't see these stars and clusters It just saw flat rows of numbers. The Graph Neural Network (GNN) we are about to build doesn't care about the specific User IDs; it is going to look at these exact pictures and mathematically learn to recognize a "Star" and a "Cluster".

3. Fast Cashout for Withdrawals
In mobile money, fraudsters rarely keep stolen money in their digital wallets for long. They quickly move it to a rogue Agent to withdraw cash.Run this command to visualize:
    MATCH p=(u:User)-[r:WITHDRAWAL]->(a:Agent) WHERE r.is_fraud = 1 RETURN p LIMIT 50
 The query above shows the "sinkholes" where stolen funds exit the system. What to look for is : You should see multiple different Users all withdrawing from the exact same Agent. This visually proves the Agent is complicit in the fraud ring

 4. Laundering via Till
 Run this:
    MATCH p=(u:User)-[r:PAYMENT]->(a:Agent) WHERE r.is_fraud = 1 RETURN p LIMIT 50
What to look for??Similar to the cashouts, look for a dense cluster of unrelated users all making payments to a single "Agent" node.

5. Reversal scams.
This is the classic social engineering scam: a fraudster sends money, calls the victim claiming they sent it to the wrong number, convinces the victim to send it back, and then triggers an official reversal to double their money. Run this :
    MATCH p=(u1:User)-[r:REVERSAL_REQUEST]->(u2:User) WHERE r.is_fraud = 1 RETURN p LIMIT 50
What to look for?? Isolated pairs of nodes (1-to-1 connections) rather than large clusters, representing individual targeted attacks.

6. Sim Swap Device Ring
This is the most important query of all. Traditional Machine Learning (like your XGBoost) can  NEVERR see this, but our GNN will. This query doesn't just look at the money; it looks at the  Phones(devices). Run this:
    MATCH p=(u1:User)-[r1:P2P_TRANSFER {is_fraud: 1}]->(u2:User), (u1)-[r2:USES]->(d:Device) 
    RETURN p, r2, d LIMIT 50
What to look for ??? Double-click the nodes to expand them. You will literally see the "Mulot SIM Swap" shape: Multiple different User accounts all connected to a single physical device node This proves that a single fraudster is swapping SIM cards into one phone to run their scam.
 

 When we converted our database into PyTorch tensors, we applied mathematical scaling (normalization). If a user's age was accidentally divided by zero, it creates a NaN (Not a Number). A single NaN in your dataset will instantly destroy the Graph Neural Network during training. Check on test if you have tensors.py then run:
    python tests/test_tensors.py
Expected results:
    User Matrix Shape: torch.Size([5999, 4])
    Any NaNs in Users?: False
    P2P Amounts Min: -1.4547
    P2P Amounts Max: 6.1238
    Any NaNs in Amounts?: False
Interpretation of the above:
    Any NaNs: False: This is the biggest hurdle in deep learning. We successfully processed nearly 6,000 users and tens of thousands of features without a single mathematical error (like dividing by zero or missing a value). Our PyTorch tensors are completely clean.
    P2P Amounts (-1.45 to 6.12): This is beautiful. In the real world, a user might send 50,000 shillings. If you feed the number "50,000" directly into a neural network, the math blows up (this is called the "exploding gradient" problem). Our pipeline successfully applied Z-score normalization, shrinking all the transaction amounts into a tight, manageable mathematical scale centered around zero.


Now we do our last test which is trying to break the system. We will have 3 scenarios:
Free Money Glitch - talks of Did any transaction accidentally get recorded with a negative or zero amount?.Run this to confirm:
    MATCH ()-[r]->() 
    WHERE type(r) IN ['P2P_TRANSFER', 'PAYMENT', 'WITHDRAWAL', 'LOAN_DISBURSEMENT'] AND r.amount <= 0 
    RETURN r LIMIT 10

Rogue user glitch - talks of , In our rules, only Institutions can disburse loans. Did a standard User accidentally become a bank and hand out a loan?Run this:
    MATCH p=(u:User)-[r:LOAN_DISBURSEMENT]->() 
    RETURN p LIMIT 10

Ghost Device glitch - This means, Every phone or should belong to a human (User). Are there any floating devices in the database that no one has ever used?Run this:
    MATCH (d:Device) 
    WHERE NOT ()-[:USES]->(d) 
    RETURN d LIMIT 10

In the 3 test, the expected result is: No changes,no records. This proves that the logic and math is okay.
Now run:
    python ml_pipeline/models/gnn_embeddings.py
Everyone will run and get different values but convergence will show you our neural network has just learned the shape.The interpretation means:
The Convergence:Our Loss started at 0.1401 and smoothly slid all the way down to 0.0172. It didn't bounce around randomly, and it didn't instantly drop to zero. This proves the neural network actually learned the shape of the data steadily over time rather than just memorizing it.
The Extraction: We successfully bypassed the Black Box problem of Deep Learning. By saving the brain to user_embeddings.csv, we have converted impossible-to-read network topologies into simple rows and columns.

The system underwent a major revision focused on improving both data representation (features) and model effectiveness (parameters). This involved expanding the feature space to better capture fraud behavior, incorporating more advanced model parameters as advised by supervisors, and ultimately redesigning the dataset. As a result, a new database was created and the previous version was discarded to ensure consistency with the updated architecture.

OUR FINAL DATASET SUMMARY:Fraud-Intel
Users: 10,000
Transactions: 100,000
Agents: 400
Devices: 5,000
Fraud Rate: 2.5% (2,500 transactions)
Time Span: 45 days
Fraud Types:
Agent Reversal Rings (25%)
Mule / SIM Swap (20%)
Fast Cash-Out (20%)
Loan Fraud Circles (15%)
Business Till Fraud (20%)

We are revising the system by expanding features and refining model parameters, creating a new database, and discarding the old one to align with the improved fraud detection design.

Feature Engineering Pipeline

Running:
python ml_pipeline/features/feature_engineering.py
Successfully engineering 17 advanced tabular features
Running:
python ml_pipeline/features/graph_features.py
Successfully adding 5 graph topology features using NetworkX (for ring detection signals)

Data Pipeline Execution (New DB).
Running sequentially:
python ml_pipeline/data_gen/generate_data.py - Generating 100K transaction dataset (CSV)
python ml_pipeline/graph_builder/neo4j_loader.py - Loading data into Neo4j graph database.
python ml_pipeline/features/feature_engineering.py -Computing tabular features
python ml_pipeline/features/graph_features.py - Computing graph/topological features
python ml_pipeline/models/graph_dataset.py - Converting processed data into PyTorch tensors

Running Existing Tests
python tests/test_tensors.py
python tests/test_pipeline.py -v
All tests are passing successfully
User tensor shape: `torch.Size([10000, 13])`
No NaN values detected
Fraud labels: 2864 (~2.8%), showing realistic imbalance due to injected fraud patterns

Database Validation (Neo4j)
MATCH (n) RETURN labels(n) AS NodeType, count(n) AS TotalCount - Counting nodes
MATCH ()-[r]->() RETURN type(r) AS EdgeType, count(r) AS TotalCount - Counting relationships

Glitch Checks
Free Money Glitch      
MATCH ()-[r:P2P_TRANSFER]->() 
WHERE r.amount <= 0 
RETURN r LIMIT 10
Ghost Device
MATCH (d:Device) 
WHERE NOT ()-[:USES]->(d) 
RETURN d LIMIT 10
Ghost Agent
MATCH (a:Agent) 
WHERE NOT ()-[:INTERACTS_WITH]->(a) 
RETURN a LIMIT 10

Visual Topology Inspection
Mule / SIM Swap Network
MATCH (u:User)-[:USES]->(d:Device)
WITH d, count(u) as user_count
WHERE user_count > 2
MATCH path=(users:User)-[:USES]->(d)
RETURN path LIMIT 50

Fraud Ring
MATCH p=(u1:User)-[r:P2P_TRANSFER {fraud_scenario: 'fraud_ring'}]->(u2:User)
RETURN p LIMIT 50

Fast Cashout
MATCH p=(u1:User)-[r:P2P_TRANSFER {fraud_scenario: 'fast_cashout'}]->(u2:User)
RETURN p LIMIT 50

 Week 4 Model Testing
pytest tests/test_gnn.py -v
-Expect all GNN tests to pass

python baseline_xgboost.py (use correct path)

From this,XGBoost is performing strongly on time/amount-based fraud (fast cashout, business fraud) but is failing to detect network-based fraud patterns like rings and SIM swaps.

GNN Evaluation
python evaluate_gnn.py (use your correct path)
GNN is improving recall by capturing hidden network relationships that XGBoost misses, especially in SIM swap and loan fraud.
However, GNN alone has low precision, making the hybrid (GNN + XGBoost) approach necessary for balanced performance.

Manual Inspection
python ml_pipeline/models/manual_inspect.py
GNN is significantly improving detection of relational fraud (SIM swap, loan fraud) by learning network structures.
However, it struggles with time-based fraud like fast cashout where XGBoost performs better.
This confirms that combining GNN (for recall) and XGBoost (for precision) is the optimal solution.

Successful tests -Test forward pass, Test embedding dimensions , Test loss computation ,Test inference on small dataset.

## CARO HAS PENDING WORK KINDLY REVISIT AND UPDATE THIS BIT.

PHASE 3: INTEGRATION PHASE:
backend + Model Integration.
kindly run this :
Install the required packages:
   pip install -r requirements.txt
   Then after that:
   1. Database Population
Before running the API, the historical transaction graph must be mapped into Neo4j.
run:
# Uploads 100k+ transactions into Neo4j using UNWIND/MERGE batching
python populate_neo4j.py

2. Start the API Server
either go to backend - cd backend
then run uvicorn main:app --reload 
or
 uvicorn backend.main:app --reload
 this 
 Starts the FastAPI server on [http://127.0.0.1:8000](http://127.0.0.1:8000)
 Note: The server dynamically locates the hybrid_xgboost.pkl model using absolute OS pathing to ensure stability

 3. Run Integration Tests
  Simulates a full Request -> DB -> Model -> Response pipeline
 run :python tests/test_api.py
 