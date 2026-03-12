import pandas as pd
import torch
from torch_geometric.data import HeteroData
from neo4j import GraphDatabase
from sklearn.preprocessing import LabelEncoder, OneHotEncoder
import numpy as np
import os

# === Configuration ===
URI = "neo4j://localhost:7687"
# UPDATE WITH YOUR NEO4J PASSWORD HERE!
AUTH = ("neo4j", "12345678") 
DATA_PATH = 'data/processed/hetero_graph.pt'
os.makedirs('data/processed', exist_ok=True)

class Neo4jGraphBuilder:
    def __init__(self, uri, auth):
        self.driver = GraphDatabase.driver(uri, auth=auth)
        self.data = HeteroData()
        # Mappings from string IDs to integer indices
        self.user_map = {}
        self.agent_map = {}
        self.device_map = {}
        self.institution_map = {}

    def close(self):
        self.driver.close()

    def run_query(self, query):
        with self.driver.session() as session:
            result = session.run(query)
            return [record.data() for record in result]

    def build_nodes(self):
        print("Processing Nodes...")
        
        # --- 1. Users ---
        users = self.run_query("MATCH (u:User) RETURN u.user_id AS id, u.account_age_days AS age, u.kyc_level AS kyc")
        users_df = pd.DataFrame(users)
        # Map IDs
        self.user_map = {userid: i for i, userid in enumerate(users_df['id'])}
        # Process Features
        kyc_encoder = OneHotEncoder(sparse_output=False)
        kyc_encoded = kyc_encoder.fit_transform(users_df[['kyc']])
        age_tensor = torch.tensor(users_df['age'].values, dtype=torch.float).view(-1, 1)
        # Normalize age
        age_tensor = (age_tensor - age_tensor.mean()) / age_tensor.std()
        
        self.data['user'].x = torch.cat([age_tensor, torch.tensor(kyc_encoded, dtype=torch.float)], dim=1)
        self.data['user'].num_nodes = len(users_df)
        print(f"  - Processed {len(users_df)} Users.")

        # --- 2. Agents ---
        agents = self.run_query("MATCH (a:Agent) RETURN a.agent_id AS id, a.agent_type AS type, a.location AS loc")
        agents_df = pd.DataFrame(agents)
        self.agent_map = {agentid: i for i, agentid in enumerate(agents_df['id'])}
        # Encoders
        type_encoder = OneHotEncoder(sparse_output=False)
        loc_encoder = OneHotEncoder(sparse_output=False)
        type_encoded = type_encoder.fit_transform(agents_df[['type']])
        loc_encoded = loc_encoder.fit_transform(agents_df[['loc']])
        
        self.data['agent'].x = torch.cat([torch.tensor(type_encoded, dtype=torch.float), 
                                          torch.tensor(loc_encoded, dtype=torch.float)], dim=1)
        self.data['agent'].num_nodes = len(agents_df)
        print(f"  - Processed {len(agents_df)} Agents.")

        # --- 3. Devices ---
        devices = self.run_query("MATCH (d:Device) RETURN d.device_id AS id, d.is_rooted AS rooted")
        devices_df = pd.DataFrame(devices)
        self.device_map = {devid: i for i, devid in enumerate(devices_df['id'])}
        # Convert boolean to float tensor
        self.data['device'].x = torch.tensor(devices_df['rooted'].values, dtype=torch.float).view(-1, 1)
        self.data['device'].num_nodes = len(devices_df)
        print(f"  - Processed {len(devices_df)} Devices.")
        
        # --- 4. Institutions ---
        institutions = self.run_query("MATCH (i:Institution) RETURN i.institution_id AS id")
        inst_df = pd.DataFrame(institutions)
        self.institution_map = {instid: i for i, instid in enumerate(inst_df['id'])}
        # Institutions might not have inherent features other than identity, use dummy feature
        self.data['institution'].x = torch.ones((len(inst_df), 1), dtype=torch.float)
        self.data['institution'].num_nodes = len(inst_df)
        print(f"  - Processed {len(inst_df)} Institutions.")


    def build_edges(self):
        print("\nProcessing Edges...")
        
        # Helper function to build edge index tensor
        def create_edge_index(source_map, target_map, records, src_key, tgt_key):
            src_indices = [source_map[rec[src_key]] for rec in records]
            tgt_indices = [target_map[rec[tgt_key]] for rec in records]
            return torch.tensor([src_indices, tgt_indices], dtype=torch.long)

        # --- Transaction Edges (P2P, Payment, Withdrawal, Loan, Reversal) ---
        # We also need edge features (amount, timestamp) and labels for these
        
        tx_query = """
        MATCH (s)-[t]->(r)
        WHERE type(t) IN ['P2P_TRANSFER', 'PAYMENT', 'WITHDRAWAL', 'LOAN_DISBURSEMENT', 'REVERSAL_REQUEST']
        RETURN s.user_id AS sid, s.agent_id AS said, s.institution_id AS siid,
               r.user_id AS rid, r.agent_id AS raid,
               type(t) AS type, t.amount AS amount, t.timestamp AS time, t.is_fraud AS label
        """
        txs = self.run_query(tx_query)
        tx_df = pd.DataFrame(txs)
        
        # Normalize Amounts
        amount_tensor = torch.tensor(tx_df['amount'].values, dtype=torch.float).view(-1, 1)
        amount_tensor = (amount_tensor - amount_tensor.mean()) / (amount_tensor.std() + 1e-6)

        # Define Edge Types based on source/target combinations
        p2p = tx_df[tx_df['type'] == 'P2P_TRANSFER']
        self.data['user', 'p2p', 'user'].edge_index = create_edge_index(self.user_map, self.user_map, p2p.to_dict('records'), 'sid', 'rid')
        self.data['user', 'p2p', 'user'].edge_attr = amount_tensor[p2p.index]
        self.data['user', 'p2p', 'user'].y = torch.tensor(p2p['label'].values, dtype=torch.long)

        pay = tx_df[tx_df['type'] == 'PAYMENT']
        self.data['user', 'pay', 'agent'].edge_index = create_edge_index(self.user_map, self.agent_map, pay.to_dict('records'), 'sid', 'raid')
        self.data['user', 'pay', 'agent'].edge_attr = amount_tensor[pay.index]
        self.data['user', 'pay', 'agent'].y = torch.tensor(pay['label'].values, dtype=torch.long)

        cash = tx_df[tx_df['type'] == 'WITHDRAWAL']
        self.data['user', 'cash_out', 'agent'].edge_index = create_edge_index(self.user_map, self.agent_map, cash.to_dict('records'), 'sid', 'raid')
        self.data['user', 'cash_out', 'agent'].edge_attr = amount_tensor[cash.index]
        self.data['user', 'cash_out', 'agent'].y = torch.tensor(cash['label'].values, dtype=torch.long)
        
        loan = tx_df[tx_df['type'] == 'LOAN_DISBURSEMENT']
        self.data['institution', 'lends', 'user'].edge_index = create_edge_index(self.institution_map, self.user_map, loan.to_dict('records'), 'siid', 'rid')
        self.data['institution', 'lends', 'user'].edge_attr = amount_tensor[loan.index]
        self.data['institution', 'lends', 'user'].y = torch.tensor(loan['label'].values, dtype=torch.long)

        rev = tx_df[tx_df['type'] == 'REVERSAL_REQUEST']
        self.data['user', 'requests_reversal', 'user'].edge_index = create_edge_index(self.user_map, self.user_map, rev.to_dict('records'), 'sid', 'rid')
        self.data['user', 'requests_reversal', 'user'].edge_attr = amount_tensor[rev.index]
        self.data['user', 'requests_reversal', 'user'].y = torch.tensor(rev['label'].values, dtype=torch.long)
        
        print(f"  - Processed {len(tx_df)} financial transactions.")

        # --- Structural Edges (User USES Device) ---
        uses = self.run_query("MATCH (u:User)-[:USES]->(d:Device) RETURN u.user_id AS uid, d.device_id AS did")
        self.data['user', 'uses', 'device'].edge_index = create_edge_index(self.user_map, self.device_map, uses, 'uid', 'did')
        print(f"  - Processed {len(uses)} device usage relationships.")

    def save_dataset(self):
        print(f"\nSaving HeteroData object to {DATA_PATH}...")
        torch.save(self.data, DATA_PATH)
        print("Dataset successfully created and saved!")
        print("\nGraph Summary:")
        print(self.data)

if __name__ == "__main__":
    builder = Neo4jGraphBuilder(URI, AUTH)
    try:
        builder.build_nodes()
        builder.build_edges()
        builder.save_dataset()
    finally:
        builder.close()