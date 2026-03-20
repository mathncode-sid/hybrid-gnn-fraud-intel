import torch
import torch.nn.functional as F
from torch_geometric.nn import SAGEConv, to_hetero
import torch_geometric.transforms as T
import pandas as pd
import os

#  1. Load the Heterogeneous Graph 
GRAPH_PATH = 'data/processed/hetero_graph.pt'
data = torch.load(GRAPH_PATH, weights_only=False)

# Make the graph undirected so information flows both ways
data = T.ToUndirected()(data)
#  2. Define the Neural Network Architecture (Using GraphSAGE for its inductive capabilities)
class GNNEncoder(torch.nn.Module):
    def __init__(self, hidden_channels, out_channels):
        super().__init__()
        # The (-1, -1) tells PyTorch to automatically figure out the input matrix dimensions!
        self.conv1 = SAGEConv((-1, -1), hidden_channels)
        self.conv2 = SAGEConv((-1, -1), out_channels)

    def forward(self, x, edge_index):
        # Message passing layer 1
        x = self.conv1(x, edge_index).relu()
        # Message passing layer 2
        x = self.conv2(x, edge_index)
        return x

class EdgeClassifier(torch.nn.Module):
    def __init__(self, hidden_channels):
        super().__init__()
        # Takes the Sender's embedding + Receiver's embedding (so 2 * hidden_channels)
        self.lin1 = torch.nn.Linear(2 * hidden_channels, hidden_channels)
        self.lin2 = torch.nn.Linear(hidden_channels, 1)

    def forward(self, z_dict, edge_index, sender_type, receiver_type):
        row, col = edge_index
        sender_z = z_dict[sender_type][row]
        receiver_z = z_dict[receiver_type][col]
        
        # Concatenate sender and receiver to evaluate the relationship
        z = torch.cat([sender_z, receiver_z], dim=-1)
        z = self.lin1(z).relu()
        z = self.lin2(z)
        return z.view(-1)

class HybridGNN(torch.nn.Module):
    def __init__(self, hidden_channels):
        super().__init__()
        # 1. Create the base encoder
        self.encoder = GNNEncoder(hidden_channels, hidden_channels)
        # 2. Automatically upgrade it to handle our Heterogeneous Nodes (Users, Agents, Devices)
        self.encoder = to_hetero(self.encoder, data.metadata(), aggr='mean')
        # 3. Add the edge classifier
        self.classifier = EdgeClassifier(hidden_channels)

    def forward(self, x_dict, edge_index_dict, target_edge_index, sender_type, receiver_type):
        # Generate structural embeddings for everyone
        z_dict = self.encoder(x_dict, edge_index_dict)
        # Predict fraud on the specified edges
        return self.classifier(z_dict, target_edge_index, sender_type, receiver_type)

#  3. Training Setup 
# Use GPU if available, otherwise CPU
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
data = data.to(device)

# Initialize model with 64-dimensional embeddings
model = HybridGNN(hidden_channels=64).to(device)
optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
criterion = torch.nn.BCEWithLogitsLoss()

#  training the network structure using the P2P transfers
train_edges = data['user', 'p2p', 'user'].edge_index
# Convert labels to float for the loss function
train_labels = data['user', 'p2p', 'user'].y.float()

#  4. Training Loop 
print("Training GNN to learn the Synecdoche & Mulot topologies...")
model.train()
for epoch in range(1, 101):
    optimizer.zero_grad()
    
    # Forward pass: Predict fraud on P2P edges
    out = model(data.x_dict, data.edge_index_dict, train_edges, 'user', 'user')
    
    # Calculate loss
    loss = criterion(out, train_labels)
    loss.backward()
    optimizer.step()
    
    if epoch % 10 == 0:
        print(f'Epoch {epoch:03d}, Loss: {loss.item():.4f}')

#  5. Extract and Save Embeddings 
print("\nExtracting learned structural embeddings...")
model.eval()
with torch.no_grad():
    final_embeddings = model.encoder(data.x_dict, data.edge_index_dict)
    # Pull the mathematical profiles of the Users out of the GPU
    user_embeddings = final_embeddings['user'].cpu().numpy()

# Save them to a CSV so XGBoost can read them later
os.makedirs('data/processed', exist_ok=True)
embed_df = pd.DataFrame(user_embeddings)
# Add an ID column so we can join it back to the original tabular data later
embed_df.insert(0, 'user_id', [f"U_{i}" for i in range(len(embed_df))])
embed_df.to_csv('data/processed/user_embeddings.csv', index=False)

print("Saved User embeddings to data/processed/user_embeddings.csv!")