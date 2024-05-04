import subprocess
import time
import psycopg2
from confluent_kafka import Producer, Consumer, KafkaError

# Check if PostgreSQL and Kafka broker are running
postgres_host = "postgres"
postgres_port = 5432
postgres_user = "postgres"
postgres_password = "postgres"
postgres_database = "voting"

kafka_host = "broker"
kafka_port = 29092


# Run generate_data.py
subprocess.run(["python3", "generate_data.py"])

# Wait for generate_data.py to finish
subprocess.run(["wait"])

# Run simulate_voting.py in background
subprocess.Popen(["python3", "simulate_voting.py"])

# Sleep for 10 seconds
time.sleep(10)

# Run spark_streaming.py in background
subprocess.Popen(["python3", "spark_streaming.py"])
