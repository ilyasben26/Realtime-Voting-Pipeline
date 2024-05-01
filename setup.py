import subprocess
import re
import time
import os

# Start the containers
subprocess.run(["docker-compose", "up", "-d", "--build"], check=True)

print("Waiting for pyspark-notebook container to be healthy...")

# Wait for the notebook container to be healthy
while True:
    health = subprocess.run(["docker", "inspect", "--format={{.State.Health.Status}}", "pyspark"], capture_output=True, text=True)
    if health.stdout.strip() == "healthy":
        print("Jupyter notebook is available.")
        break
    print("Still waiting for pyspark-notebook container to be healthy...")
    time.sleep(5)

print("Extracting URL from container logs...")

# Get the URL from the logs
logs = subprocess.run(["docker-compose", "logs", "pyspark"], capture_output=True, text=True)
url_match = re.search(r'(http://127\.0\.0\.1:8888/lab\?token=\S+)', logs.stdout)
if url_match:
    url = url_match.group(0)
    print("Jupyter notebook is available at:")
    print(url)
else:
    print("Failed to retrieve URL.")
