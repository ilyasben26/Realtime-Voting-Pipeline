import subprocess
import time

# Start the containers
subprocess.run(["docker-compose", "up", "-d", "--build"], check=True)

# Function to check if a container is healthy
def is_container_healthy(container_name):
    result = subprocess.run(["docker", "inspect", "--format='{{.State.Health.Status}}'", container_name], capture_output=True, text=True)
    return result.stdout.strip() == "'healthy'"

# Wait for all the containers to become healthy
print("Waiting for containers to become healthy...")
while not (is_container_healthy("postgres") and is_container_healthy("broker")):
    time.sleep(5)  # Adjust the interval between checks if needed

# Once both containers are healthy, run the script inside the pyspark container
print("All containers are healthy. Proceeding to run the script.")
subprocess.run(["docker", "exec", "pyspark", "python", "run_all.py"], check=True)

# Wait for the Streamlit container to become healthy
print("Waiting for the Streamlit container to become healthy...")
while not is_container_healthy("streamlit"):
    time.sleep(5)  # Adjust the interval between checks if needed

print("Streamlit app accessible at: http://localhost:8501")