import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
import os

print(" Phase 1: Generating Master's-Level Synthetic Dataset ")

# 1. GLOBAL SETTINGS (Upgraded per research)
NUM_USERS = 10000        
NUM_TRANSACTIONS = 100000 
NUM_AGENTS = 400         
NUM_DEVICES = 5000        
FRAUD_RATE = 0.025       # 2.5% fraud rate 

START_DATE = datetime(2025, 1, 1)
DAYS = 45                # 45-day timeline for temporal depth 

# 2. CREATE ENTITIES
users = [f"U_{i}" for i in range(NUM_USERS)]
agents = [f"A_{i}" for i in range(NUM_AGENTS)]
devices = [f"D_{i}" for i in range(NUM_DEVICES)]

# 3. HELPER FUNCTIONS
def random_time():
    return START_DATE + timedelta(seconds=random.randint(0, DAYS * 24 * 3600))

def random_amount():
    return round(np.random.exponential(scale=2000), 2)

# 4. GENERATE NORMAL TRANSACTIONS
data = []
num_fraud = int(NUM_TRANSACTIONS * FRAUD_RATE)
num_normal = NUM_TRANSACTIONS - num_fraud

print(f"Generating {num_normal} normal transactions...")
for _ in range(num_normal):
    data.append({
        "sender_id": random.choice(users),
        "receiver_id": random.choice(users),
        "amount": random_amount(),
        "timestamp": random_time(),
        "agent_id": random.choice(agents),
        "device_id": random.choice(devices),
        "is_fraud": 0,
        "fraud_scenario": "none"
    })

# 5. FRAUD GENERATORS (The 5 Specific Topologies)
print(f"Injecting {num_fraud} fraudulent transactions across 5 topologies...")

def generate_fraud_ring(size=4):
    nodes = random.sample(users, size)
    for i in range(size):
        data.append({
            "sender_id": nodes[i],
            "receiver_id": nodes[(i + 1) % size],
            "amount": random_amount() * 5,
            "timestamp": random_time(),
            "agent_id": random.choice(agents),
            "device_id": random.choice(devices),
            "is_fraud": 1,
            "fraud_scenario": "fraud_ring"
        })

def generate_mule_cluster(size=5):
    device = random.choice(devices) # Shared device
    central = random.choice(users)
    for _ in range(size):
        data.append({
            "sender_id": random.choice(users),
            "receiver_id": central,
            "amount": random_amount(),
            "timestamp": random_time(),
            "agent_id": random.choice(agents),
            "device_id": device,
            "is_fraud": 1,
            "fraud_scenario": "mule_sim_swap"
        })

def generate_fast_cashout(size=5):
    origin = random.choice(users)
    base_time = random_time()
    for _ in range(size):
        data.append({
            "sender_id": origin,
            "receiver_id": random.choice(users),
            "amount": random_amount() * 3,
            "timestamp": base_time + timedelta(seconds=random.randint(0, 60)), # Burst!
            "agent_id": random.choice(agents),
            "device_id": random.choice(devices),
            "is_fraud": 1,
            "fraud_scenario": "fast_cashout"
        })

def generate_loan_cluster(size=5):
    cluster = random.sample(users, size)
    for u1 in cluster:
        for u2 in cluster:
            if u1 != u2:
                data.append({
                    "sender_id": u1,
                    "receiver_id": u2,
                    "amount": random_amount(),
                    "timestamp": random_time(),
                    "agent_id": random.choice(agents),
                    "device_id": random.choice(devices),
                    "is_fraud": 1,
                    "fraud_scenario": "loan_fraud"
                })

def generate_business_fraud(size=5):
    u1, u2 = random.choice(users), random.choice(users)
    for _ in range(size):
        data.append({
            "sender_id": u1,
            "receiver_id": u2,
            "amount": random_amount(),
            "timestamp": random_time(),
            "agent_id": random.choice(agents),
            "device_id": random.choice(devices),
            "is_fraud": 1,
            "fraud_scenario": "business_fraud"
        })

# 6. DISTRIBUTE FRAUD TYPES
fraud_counts = {
    "fraud_ring": int(0.25 * num_fraud),      # 25% 
    "mule": int(0.20 * num_fraud),            # 20% 
    "fast_cashout": int(0.20 * num_fraud),    # 20% 
    "loan_fraud": int(0.15 * num_fraud),      # 15% 
    "business_fraud": int(0.20 * num_fraud)   # 20% 
}

# Inject the exact mathematical proportions
for _ in range(fraud_counts["fraud_ring"] // 4): generate_fraud_ring()
for _ in range(fraud_counts["mule"] // 5): generate_mule_cluster()
for _ in range(fraud_counts["fast_cashout"] // 5): generate_fast_cashout()
for _ in range(fraud_counts["loan_fraud"] // 10): generate_loan_cluster()
for _ in range(fraud_counts["business_fraud"] // 5): generate_business_fraud()

# 7. EXPORT TO CSV
df = pd.DataFrame(data)
df = df.sample(frac=1).reset_index(drop=True) # Shuffle the timeline

os.makedirs('data/raw', exist_ok=True)
df.to_csv("data/raw/p2p_transfers.csv", index=False)

print("\nSuccess! Generated 100,000 transactions.")
print("Saved to: data/raw/p2p_transfers.csv")