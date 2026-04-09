"""
Graph Consumer: Consumes transactions from Kafka
Updates Neo4j graph and calls FastAPI prediction endpoint
"""

import json
import requests
import time
from kafka import KafkaConsumer
from neo4j import GraphDatabase

KAFKA_BROKER = 'localhost:9092'
KAFKA_TOPIC = 'transactions'
KAFKA_GROUP = 'fraud-detection-group'

NEO4J_URI = "neo4j://localhost:7687"
NEO4J_AUTH = ("neo4j", "12345678")

FASTAPI_URL = "http://127.0.0.1:8000/predict"

class GraphConsumer:
    def __init__(self):
        """Initialize Kafka consumer and Neo4j driver"""
        self.consumer = None
        self.driver = None
        self.processed_count = 0
        
        # Initialize Kafka
        try:
            self.consumer = KafkaConsumer(
                KAFKA_TOPIC,
                bootstrap_servers=KAFKA_BROKER,
                group_id=KAFKA_GROUP,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                max_poll_records=100
            )
            print(f"✅ Consumer connected to Kafka: {KAFKA_BROKER}")
        except Exception as e:
            print(f"❌ Failed to connect to Kafka: {e}")
            return
        
        # Initialize Neo4j
        try:
            self.driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
            self.driver.verify_connectivity()
            print(f"✅ Connected to Neo4j: {NEO4J_URI}")
        except Exception as e:
            print(f"❌ Failed to connect to Neo4j: {e}")
            self.driver = None

    def update_neo4j(self, transaction):
        """Update Neo4j graph with new transaction edge"""
        if not self.driver:
            return False
        
        try:
            with self.driver.session() as session:
                cypher = """
                MERGE (sender:User {user_id: $sender_id})
                MERGE (receiver:User {user_id: $receiver_id})
                MERGE (sender)-[tx:SENT_MONEY {transaction_id: $tx_id}]->(receiver)
                SET tx.amount = toFloat($amount), tx.timestamp = $timestamp
                """
                session.run(
                    cypher,
                    sender_id=transaction['sender_id'],
                    receiver_id=transaction['receiver_id'],
                    tx_id=transaction['transaction_id'],
                    amount=transaction['amount'],
                    timestamp=transaction['timestamp']
                )
            return True
        except Exception as e:
            print(f"❌ Neo4j Error: {e}")
            return False

    def call_fraud_detection(self, transaction):
        """Call FastAPI prediction endpoint"""
        try:
            payload = {
                "transaction_id": transaction['transaction_id'],
                "sender_id": transaction['sender_id'],
                "receiver_id": transaction['receiver_id'],
                "amount": transaction['amount'],
                "transactions_last_24hr": transaction['transactions_last_24hr'],
                "hour": transaction['hour']
            }
            response = requests.post(FASTAPI_URL, json=payload, timeout=5)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"   ⚠️  API returned {response.status_code}")
                return None
        except requests.exceptions.ConnectionError:
            print(f"   ⚠️  FastAPI not running on {FASTAPI_URL}")
            return None
        except Exception as e:
            print(f"   ⚠️  API Error: {e}")
            return None

    def process_transaction(self, transaction):
        """Process a single transaction: Neo4j + FastAPI"""
        neo4j_ok = self.update_neo4j(transaction)
        prediction = self.call_fraud_detection(transaction)
        
        self.processed_count += 1
        status = "✅" if prediction and prediction.get('decision') else "⚠️"
        
        print(f"[{self.processed_count}] {status} {transaction['transaction_id']} | "
              f"Risk: {prediction['risk_score'] if prediction else 'N/A'} | "
              f"Decision: {prediction['decision'] if prediction else 'N/A'}")

    def start(self):
        """Main consumer loop"""
        if not self.consumer:
            print("❌ Consumer failed to initialize. Exiting.")
            return
        
        print("🔄 Starting Graph Consumer...")
        print(f"   Topic: {KAFKA_TOPIC}")
        print("   Listening for transactions...")
        print("   Press Ctrl+C to stop\n")
        
        try:
            for message in self.consumer:
                transaction = message.value
                self.process_transaction(transaction)
        
        except KeyboardInterrupt:
            print(f"\n🛑 Consumer stopped. Processed {self.processed_count} transactions total.")
        finally:
            self.consumer.close()
            if self.driver:
                self.driver.close()

if __name__ == "__main__":
    consumer = GraphConsumer()
    consumer.start()
