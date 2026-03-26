import pandas as pd
import numpy as np
import os
from datetime import timedelta

print(" Phase 1.5: Feature Engineering ")

# 1. Load the Raw Data
print("Loading raw transactions...")
df = pd.read_csv('data/raw/p2p_transfers.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# 2. DEVICE FEATURES: Detect Shared Devices (SIM Swap / Mule Indicator)
print("Calculating Device Features (num_accounts_linked)...")
# Count how many unique users are tied to each device
device_user_counts = df.groupby('device_id')['sender_id'].nunique().reset_index()
device_user_counts.rename(columns={'sender_id': 'num_accounts_linked'}, inplace=True)
df = df.merge(device_user_counts, on='device_id', how='left')

# Create the shared_device_flag (If > 2 users use one device, flag it)
df['shared_device_flag'] = (df['num_accounts_linked'] > 2).astype(int)

# 3. USER FEATURES: Behavior Profiling
print("Calculating User Features (Averages and Frequencies)...")
user_stats = df.groupby('sender_id').agg(
    avg_transaction_amount=('amount', 'mean'),
    transaction_frequency=('amount', 'count'),
    num_unique_recipients=('receiver_id', 'nunique')
).reset_index()
df = df.merge(user_stats, on='sender_id', how='left')

# 4. VELOCITY FEATURES: Time-window aggregations
print("Calculating Velocity Features (24hr rolling windows)...")
# We use a rolling window to count transactions in the last 24 hours for each user
df.set_index('timestamp', inplace=True)
df['transactions_last_24hr'] = df.groupby('sender_id')['amount'].transform(
    lambda x: x.rolling('1D').count()
)
df.reset_index(inplace=True)

# 5. STRUCTURING FEATURES: Round Amounts
print("Calculating Structuring Features (round_amount_flag)...")
# Fraudsters often send clean, round numbers (e.g., exactly 5000, not 4932.50)
df['round_amount_flag'] = (df['amount'] % 100 == 0).astype(int)

# 6. TIME ANOMALIES: Night Activity
print("Calculating Time Features (night_activity)...")
# Flag transactions that happen between midnight and 5 AM
df['hour'] = df['timestamp'].dt.hour
df['night_activity_flag'] = df['hour'].apply(lambda x: 1 if 0 <= x <= 5 else 0)

# 7. EXPORT ENRICHED DATASET
os.makedirs('data/processed', exist_ok=True)
export_path = 'data/processed/enriched_transfers.csv'
df.to_csv(export_path, index=False)

print(f"\nSuccess! Engineered {len(df.columns)} advanced features.")
print(f"Saved highly enriched dataset to: {export_path}")