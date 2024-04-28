#!/bin/bash

# Start the containers
docker-compose up -d

# Wait for the notebook container to be healthy
while true; do
    HEALTH=$(docker inspect --format='{{json .State.Health.Status}}' pyspark-notebook)
    if [ "$HEALTH" == '"healthy"' ]; then
        echo "Jupyter notebook is available at:"
        break
    fi
    echo "Waiting for pyspark-notebook container to be healthy..."
    sleep 5
done

# Get the URL from the logs
URL=$(docker-compose logs pyspark-notebook 2>&1 | grep -m 1 -o 'http://127\.0\.0\.1:8888/lab?token=[^[:space:]]\+')
echo "$URL"