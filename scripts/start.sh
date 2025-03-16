#!/bin/bash
# start.sh - Start all core services for wsl-assistant

echo "===================================="
echo "Starting WSL Assistant services..."
echo "===================================="

# --- Redis Stack Server ---
echo "[1/4] Starting Redis Stack Server..."
sudo systemctl start redis-stack-server
# Give Redis a moment to start up
sleep 2
if redis-cli ping | grep -q "PONG"; then
    echo "✅ Redis Stack Server is running."
else
    echo "❌ Error: Redis Stack Server failed to start."
fi

# --- Neo4j ---
echo "[2/4] Starting Neo4j..."
sudo systemctl start neo4j
# Allow some time for Neo4j to initialize
sleep 5
neo4j_status=$(neo4j status)
if echo "$neo4j_status" | grep -q "is running"; then
    echo "✅ Neo4j is running."
else
    echo "❌ Error: Neo4j failed to start."
fi

# --- llama-server ---
echo "[3/4] Starting llama-server..."
# Check if llama-server is already running
if curl -s -X GET http://localhost:8080/health | grep -q '"status":"ok"'; then
    echo "✅ llama-server is already running."
else
    # Launch llama-server in the background. Adjust the model path if needed.
    llama-server -m SmolLM2.q8.gguf &
    sleep 2
    if pgrep -x "llama-server" > /dev/null; then
        echo "✅ llama-server started successfully."
    else
        echo "❌ Error: llama-server failed to start."
    fi
fi

# --- embed-server ---
echo "[4/5] Starting embed-server..."
# Check if embed-server is already running
if curl -s -X GET http://localhost:8000/health | grep -q '"status":"ok"'; then
    echo "✅ embed-server is already running."
else
    # Launch embed-server in the background. Adjust the model path if needed.
    llama-server --embedding --port 8000 -ngl 99 -m $HOME/models/nomic-embed-text-v1.5.Q2_K.gguf -c 8192 -b 8192 --rope-scaling yarn --rope-freq-scale .75 &
    sleep 2
    if pgrep -x "llama-server" > /dev/null; then
        echo "✅ llama-server started successfully."
    else
        echo "❌ Error: llama-server failed to start."
    fi
fi

# --- http-server ---
echo "[5/5] Starting http-server..."
# Check if http-server is already running
if curl -s -X GET http://localhost:5000/health | grep -q '"status":"ok"'; then
    echo "✅ http-server is already running."
else
    # Launch http-server in the background.
    $HOME/venv/bin/python $HOME/http-server/http-server.py &
    sleep 2
    if pgrep -x "http-server" > /dev/null; then
        echo "✅ http-server started successfully."
    else
        echo "❌ Error: http-server failed to start."
    fi
fi

echo "===================================="
echo "All services have been initiated."
echo "===================================="

