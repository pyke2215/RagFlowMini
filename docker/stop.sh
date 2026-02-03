#!/bin/bash

# Script để stop RAG Flow Mini

set -e

echo "Stopping RAG Flow Mini..."

docker-compose down

echo "All services stopped."

