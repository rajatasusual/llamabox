#!/bin/bash
set -e

echo "🔍 Running Health Check for Llamabox Setup..."

# 1. Check Redis Server
echo "Checking Redis..."
if redis-cli ping | grep -q "PONG"; then
    echo "✅ Redis is running."
else
    echo "❌ ERROR: Redis is NOT running!"
    exit 1
fi

# 2. Check Neo4j
echo "Checking Neo4j..."
if neo4j status | grep -q "is running"; then
    echo "✅ Neo4j is running."
else
    echo "❌ ERROR: Neo4j is NOT running!"
    exit 1
fi

# 3. Check Llama Server
box check_health "Llama Server" "http://localhost:8080/health" '"status":"ok"' "true" "llama-server"

# 4. Check Embed Server
box check_health "Embed Server" "http://localhost:8000/health" '"status":"ok"' "true" "embed-server"

# 5. Check Redis Worker (Checks if it's registered in Redis)
echo "Checking Redis Worker..."
if "$HOME/venv/bin/rq" info --url redis://localhost:6379 | grep -q "snippet_queue"; then
    echo "✅ Redis worker is healthy."
else
    echo "❌ ERROR: Redis worker health check failed!"
    exit 1
fi

# 6. Check HTTP Server
box check_health "HTTP Server" "http://localhost:5000/health" '"status":"ok"' "true" "http-server"

box print_header "✅ ALL SERVICES ARE RUNNING SUCCESSFULLY!"
exit 0
