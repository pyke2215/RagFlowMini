#!/bin/bash

# Script để start RAG Flow Mini với Docker

set -e

echo "Starting RAG Flow Mini..."

# Check if .env exists
if [ ! -f ../.env ]; then
    if [ -f ../env.example ]; then
        echo ".env file not found. Creating from env.example..."
        cp ../env.example ../.env
        echo "Created .env file. Please edit it with your configuration."
        read -p "Press enter to continue after editing .env..."
    else
        echo ".env file not found and env.example not found."
        echo "   Please create .env file manually."
        exit 1
    fi
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Docker is not running. Please start Docker first."
    exit 1
fi

# Check for GPU support (optional)
if command -v nvidia-smi &> /dev/null; then
    echo "NVIDIA GPU detected"
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
else
    echo "No NVIDIA GPU detected. App will run on CPU (slow)."
    echo "   Consider using OpenAI API instead of local Ollama."
fi

# Build and start services
echo "Building and starting services..."
docker-compose up -d --build

# Wait for services to be healthy
echo "Waiting for services to be ready..."
sleep 10

# Check health
echo "Checking service health..."
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo "All services are healthy!"
        break
    fi
    attempt=$((attempt + 1))
    echo "   Attempt $attempt/$max_attempts..."
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo "Services failed to start. Check logs with: docker-compose logs"
    exit 1
fi

# Show status
echo ""
echo "Service Status:"
docker-compose ps

echo ""
echo "RAG Flow Mini is running!"
echo "   API: http://localhost:8000"
echo "   Docs: http://localhost:8000/docs"
echo "   Health: http://localhost:8000/health"
echo ""
echo "Useful commands:"
echo "   View logs: docker-compose logs -f"
echo "   Stop: docker-compose down"
echo "   Restart: docker-compose restart"

