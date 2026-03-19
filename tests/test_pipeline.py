import os
import pytest
import torch
import pandas as pd
from neo4j import GraphDatabase
from sklearn.preprocessing import OneHotEncoder

#  Configuration 
URI = "neo4j://localhost:7687"
AUTH = ("neo4j", "12345678") # Update this to your actual Neo4j password!
GRAPH_FILE = 'data/processed/hetero_graph.pt'

# 1. Test Data Loader Function (Database Integrity)
def test_neo4j_connection_and_data_loader():
    """Tests if Neo4j is running and successfully loaded the synthetic data."""
    try:
        driver = GraphDatabase.driver(URI, auth=AUTH)
        with driver.session() as session:
            # Verify Users exist
            user_result = session.run("MATCH (u:User) RETURN count(u) AS count")
            user_count = user_result.single()["count"]
            assert user_count > 0, "Data Loader Failed: No Users found in Neo4j."
            
            # Verify Fraud Scenarios exist (Testing the M-Pesa topologies)
            fraud_result = session.run("MATCH ()-[r:P2P_TRANSFER {is_fraud: 1}]->() RETURN count(r) AS count")
            fraud_count = fraud_result.single()["count"]
            assert fraud_count > 0, "Data Loader Failed: No Fraud edges found."
            
        driver.close()
    except Exception as e:
        pytest.fail(f"Database connection or query failed: {e}")


# 2. Test Feature Extraction Functions (Matrix Shapes)
def test_feature_extraction_logic():
    """Tests if our categorical text features correctly translate to mathematical matrices."""
    # Mock some raw KYC data
    mock_df = pd.DataFrame({'kyc_level': ['Tier_1', 'Tier_2', 'Tier_1', 'Tier_3']})
    
    encoder = OneHotEncoder(sparse_output=False)
    encoded_matrix = encoder.fit_transform(mock_df[['kyc_level']])
    
    # We expect 3 unique columns (Tier 1, 2, 3) and 4 rows of data
    assert encoded_matrix.shape == (4, 3), f"Feature extraction failed. Expected shape (4, 3), got {encoded_matrix.shape}"


# 3. Test Graph Construction Correctness (PyTorch Geometric Tensors)
def test_pytorch_heterodata_structure():
    """Tests if the database was correctly converted into a PyTorch HeteroData object."""
    # Ensure the pipeline actually saved the file
    assert os.path.exists(GRAPH_FILE), f"Graph tensor file missing at {GRAPH_FILE}. Did you run graph_dataset.py?"
    
    # Load the math
    data = torch.load(GRAPH_FILE)
    
    # Assert all node types made it into the neural network
    expected_nodes = ['user', 'agent', 'device', 'institution']
    for node in expected_nodes:
        assert node in data.node_types, f"Graph Construction Error: Missing '{node}' nodes."
        assert data[node].num_nodes > 0, f"Graph Construction Error: '{node}' tensor is empty."
        
    # Assert complex edges exist
    assert ('user', 'p2p', 'user') in data.edge_types, "Missing User-to-User P2P edges."
    assert ('user', 'uses', 'device') in data.edge_types, "Missing User-to-Device structural edges."
    
    # Validate tensor formats (must be Float for neural network weights)
    assert data['user'].x.dtype == torch.float32, "User features must be float32 tensors."