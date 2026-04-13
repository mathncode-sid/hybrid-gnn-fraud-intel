import numpy as np
import pandas as pd
import torch
import matplotlib.pyplot as plt
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_curve, roc_auc_score
from torch_geometric.nn import SAGEConv, to_hetero

from config import get_model_config


def build_shared_split(labels, test_size=0.2, random_state=42):
    """Create one shared split so all models are compared on the same test rows."""
    indices = np.arange(len(labels))
    train_idx, test_idx = train_test_split(
        indices,
        test_size=test_size,
        random_state=random_state,
        stratify=labels,
    )
    return train_idx, test_idx


def evaluate_baseline(df, train_idx, test_idx):
    graph_features = [
        "triad_closure_score",
        "pagerank_score",
        "in_degree",
        "out_degree",
        "cycle_indicator",
    ]
    baseline_df = df.drop(columns=graph_features, errors="ignore")

    tabular_features = [
        "amount",
        "num_accounts_linked",
        "shared_device_flag",
        "avg_transaction_amount",
        "transaction_frequency",
        "num_unique_recipients",
        "transactions_last_24hr",
        "round_amount_flag",
        "night_activity_flag",
    ]

    X = baseline_df[tabular_features]
    y = baseline_df["is_fraud"].astype(int)

    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

    pos_weight = (len(y_train) - y_train.sum()) / max(y_train.sum(), 1)
    model = XGBClassifier(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        scale_pos_weight=pos_weight,
        random_state=42,
        eval_metric="logloss",
    )
    model.fit(X_train, y_train)

    probs = model.predict_proba(X_test)[:, 1]
    auc_value = roc_auc_score(y_test, probs)
    return y_test.to_numpy(), probs, auc_value


def evaluate_stacked_hybrid(df, embeddings_df, train_idx, test_idx):
    embeddings_df = embeddings_df.add_prefix("gnn_")
    hybrid_df = df.merge(
        embeddings_df,
        left_on="sender_id",
        right_on="gnn_user_id",
        how="left",
    )

    drop_cols = [
        "sender_id",
        "receiver_id",
        "timestamp",
        "device_id",
        "agent_id",
        "is_fraud",
        "fraud_scenario",
        "gnn_user_id",
    ]
    X = hybrid_df.drop(columns=drop_cols, errors="ignore")
    y = hybrid_df["is_fraud"].astype(int)

    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

    pos_weight = (len(y_train) - y_train.sum()) / max(y_train.sum(), 1)
    model = XGBClassifier(
        n_estimators=150,
        max_depth=4,
        learning_rate=0.05,
        colsample_bytree=0.6,
        scale_pos_weight=pos_weight * 1.5,
        random_state=42,
        eval_metric="logloss",
    )
    model.fit(X_train, y_train)

    probs = model.predict_proba(X_test)[:, 1]
    auc_value = roc_auc_score(y_test, probs)
    return y_test.to_numpy(), probs, auc_value


class GNNEncoder(torch.nn.Module):
    def __init__(self, hidden_channels, out_channels):
        super().__init__()
        self.conv1 = SAGEConv((-1, -1), hidden_channels)
        self.conv2 = SAGEConv((-1, -1), out_channels)

    def forward(self, x, edge_index):
        x = self.conv1(x, edge_index).relu()
        x = self.conv2(x, edge_index)
        return x


class EdgeClassifier(torch.nn.Module):
    def __init__(self, hidden_channels):
        super().__init__()
        self.lin1 = torch.nn.Linear(2 * hidden_channels, hidden_channels)
        self.lin2 = torch.nn.Linear(hidden_channels, 1)

    def forward(self, z_dict, edge_index, sender_type, receiver_type):
        row, col = edge_index
        z = torch.cat([z_dict[sender_type][row], z_dict[receiver_type][col]], dim=-1)
        z = self.lin1(z).relu()
        z = self.lin2(z)
        return z.view(-1)


class HybridGNN(torch.nn.Module):
    def __init__(self, hidden_channels, metadata):
        super().__init__()
        self.encoder = GNNEncoder(hidden_channels, hidden_channels)
        self.encoder = to_hetero(self.encoder, metadata, aggr="mean")
        self.classifier = EdgeClassifier(hidden_channels)

    def forward(self, x_dict, edge_index_dict, target_edge_index, sender_type, receiver_type):
        z_dict = self.encoder(x_dict, edge_index_dict)
        return self.classifier(z_dict, target_edge_index, sender_type, receiver_type)


def evaluate_gnn(train_idx, test_idx):
    config = get_model_config()
    embedding_dim = config["embedding_dim"]

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    data = torch.load("data/processed/hetero_graph.pt", weights_only=False).to(device)

    all_edges = data["user", "p2p", "user"].edge_index
    all_labels = data["user", "p2p", "user"].y.float()
    num_edges = all_edges.size(1)

    if max(np.max(train_idx), np.max(test_idx)) >= num_edges:
        raise ValueError(
            "Shared split indices exceed graph edge count. Ensure final_model_data rows align with p2p edges."
        )

    train_edges = all_edges[:, train_idx]
    test_edges = all_edges[:, test_idx]
    train_labels = all_labels[train_idx]
    test_labels = all_labels[test_idx]

    model = HybridGNN(hidden_channels=embedding_dim, metadata=data.metadata()).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)

    num_neg = len(train_labels) - train_labels.sum()
    pos_weight = num_neg / torch.clamp(train_labels.sum(), min=1.0)
    criterion = torch.nn.BCEWithLogitsLoss(pos_weight=pos_weight)

    model.train()
    for _ in range(100):
        optimizer.zero_grad()
        out = model(data.x_dict, data.edge_index_dict, train_edges, "user", "user")
        loss = criterion(out, train_labels)
        loss.backward()
        optimizer.step()

    model.eval()
    with torch.no_grad():
        test_out = model(data.x_dict, data.edge_index_dict, test_edges, "user", "user")
        probs = torch.sigmoid(test_out).cpu().numpy()

    y_test = test_labels.cpu().numpy().astype(int)
    auc_value = roc_auc_score(y_test, probs)
    return y_test, probs, auc_value


def save_roc_plot(curves, output_path):
    plt.figure(figsize=(9, 7))

    for label, y_true, y_score in curves:
        fpr, tpr, _ = roc_curve(y_true, y_score)
        auc_value = roc_auc_score(y_true, y_score)
        plt.plot(fpr, tpr, linewidth=2, label=f"{label} (AUC={auc_value:.4f})")

    plt.plot([0, 1], [0, 1], linestyle="--", linewidth=1, color="gray", label="Random")
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title("ROC Curve Comparison: Baseline vs GNN vs Stacked Hybrid")
    plt.legend(loc="lower right")
    plt.grid(alpha=0.25)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"Saved ROC comparison plot to: {output_path}")


def save_individual_roc_plots(curves, output_dir):
    for label, y_true, y_score in curves:
        fpr, tpr, _ = roc_curve(y_true, y_score)
        auc_value = roc_auc_score(y_true, y_score)

        plt.figure(figsize=(8, 6))
        plt.plot(fpr, tpr, linewidth=2, label=f"{label} (AUC={auc_value:.4f})")
        plt.plot([0, 1], [0, 1], linestyle="--", linewidth=1, color="gray", label="Random")
        plt.xlabel("False Positive Rate")
        plt.ylabel("True Positive Rate")
        plt.title(f"ROC Curve: {label}")
        plt.legend(loc="lower right")
        plt.grid(alpha=0.25)
        plt.tight_layout()

        safe_name = label.lower().replace(" ", "_")
        per_model_path = f"{output_dir}/roc_{safe_name}.png"
        plt.savefig(per_model_path, dpi=300)
        plt.close()
        print(f"Saved individual ROC plot to: {per_model_path}")


def main():
    print("Loading tabular and embedding data...")
    df = pd.read_csv("data/processed/final_model_data.csv")
    embeddings_df = pd.read_csv("data/processed/user_embeddings.csv")

    print("Building one shared split for all models...")
    train_idx, test_idx = build_shared_split(df["is_fraud"].astype(int))

    print("Evaluating baseline XGBoost...")
    y_base, p_base, auc_base = evaluate_baseline(df, train_idx, test_idx)

    print("Evaluating stacked hybrid XGBoost...")
    y_stack, p_stack, auc_stack = evaluate_stacked_hybrid(df, embeddings_df, train_idx, test_idx)

    print("Evaluating GNN...")
    y_gnn, p_gnn, auc_gnn = evaluate_gnn(train_idx, test_idx)

    print("\nAUC Summary")
    print(f"Baseline XGBoost AUC: {auc_base:.4f}")
    print(f"GNN AUC:              {auc_gnn:.4f}")
    print(f"Stacked Hybrid AUC:   {auc_stack:.4f}")

    output_dir = "data/processed"
    output_path = f"{output_dir}/roc_auc_comparison.png"
    curves = [
        ("Baseline XGBoost", y_base, p_base),
        ("GNN", y_gnn, p_gnn),
        ("Stacked Hybrid", y_stack, p_stack),
    ]
    save_roc_plot(curves, output_path)
    save_individual_roc_plots(curves, output_dir)

    summary_df = pd.DataFrame(
        {
            "model": ["baseline_xgboost", "evaluate_gnn", "stacked_hybrid"],
            "roc_auc": [auc_base, auc_gnn, auc_stack],
        }
    )
    summary_path = f"{output_dir}/roc_auc_summary.csv"
    summary_df.to_csv(summary_path, index=False)
    print(f"Saved ROC AUC summary table to: {summary_path}")

    print("\nReporting guidance:")
    print("Primary figure: use the combined ROC comparison chart in the main narrative.")
    print("If examiners ask for detail, add per-model standalone ROC plots as supplementary material, but not required for the main narrative.")
    print("This script automatically saves three individual ROC images in addition to the combined plot.")


if __name__ == "__main__":
    main()