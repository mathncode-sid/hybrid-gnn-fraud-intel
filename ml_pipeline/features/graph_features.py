import pandas as pd
import networkx as nx
import os

print("--- Phase 1.7: Topological Graph Features (NetworkX) ---")

# 1. Load the Enriched Data
print("Loading the 17-feature dataset...")
df = pd.read_csv('data/processed/enriched_transfers.csv')

# 2. Build the Directed Graph in RAM
print("Building NetworkX Directed Graph from 100,000 transactions...")
G = nx.from_pandas_edgelist(
    df,
    source='sender_id',
    target='receiver_id',
    create_using=nx.DiGraph()
)

# 3. Calculate Triad Closure Score (Clustering Coefficient)
# This answers: "How likely are a user's transaction partners to also transact with each other?"
print("Calculating Triad Closure Scores...")
clustering_coeffs = nx.clustering(G)
df['triad_closure_score'] = df['sender_id'].map(clustering_coeffs)

# 4. Calculate Network Centrality (PageRank)
# Identifies "Hubs" (like central money mules or rogue agents)
print("Calculating PageRank (Hub/Mule Score)...")
pagerank = nx.pagerank(G, alpha=0.85)
df['pagerank_score'] = df['sender_id'].map(pagerank)

# 5. Calculate In-Degree and Out-Degree
print("Calculating Transaction Degrees...")
in_degrees = dict(G.in_degree())
out_degrees = dict(G.out_degree())
df['in_degree'] = df['sender_id'].map(in_degrees)
df['out_degree'] = df['sender_id'].map(out_degrees)

# 6. Calculate Cycle Indicator (Reciprocity)
# Measures how often money flows in circular/reciprocal paths (A -> B -> A)
print("Calculating Cycle Indicators...")
reciprocal_edges = nx.reciprocity(G, nodes=G.nodes)
df['cycle_indicator'] = df['sender_id'].map(reciprocal_edges)

# 7. Save the Final Ultimate Dataset
export_path = 'data/processed/final_model_data.csv'
df.to_csv(export_path, index=False)

print(f"\nSuccess! Added 5 structural graph features. Total columns: {len(df.columns)}")
print(f"Saved defense-ready dataset to: {export_path}")