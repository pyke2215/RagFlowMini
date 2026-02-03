# Docker Setup Guide - RAG Flow Mini

Hướng dẫn setup và chạy RAG Flow Mini với Docker.

## Yêu Cầu

- Docker Engine 20.10+
- Docker Compose 2.0+
- NVIDIA Docker (nếu dùng GPU) - [Install Guide](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)
- NVIDIA GPU với CUDA 12.6+ (khuyến nghị)

## Quick Start

### 1. Clone và chuẩn bị

```bash
# Clone repository (nếu chưa có)
git clone <repository-url>
cd RagFlow_Mini

# Copy file .env.example
cp .env.example .env

# Chỉnh sửa .env với cấu hình của bạn
nano .env
```

### 2. Build và chạy với Docker Compose

```bash
# Chạy từ thư mục docker
cd docker

# Build và start tất cả services
docker-compose up -d

# Xem logs
docker-compose logs -f

# Xem logs của service cụ thể
docker-compose logs -f ragflow_app
```

### 3. Kiểm tra services

```bash
# Check health
curl http://localhost:8000/health

# Test API
curl http://localhost:8000/docs
```

## Cấu Hình

### Environment Variables

Chỉnh sửa file `.env` ở root directory với các giá trị phù hợp:

- **EMBEDDING_MODEL**: Model embedding (mặc định: BAAI/bge-m3)
- **LLM_PROVIDER**: ollama hoặc openai
- **LLM_BASE_URL**: URL của LLM service
- **MONGODB_URI**: Connection string MongoDB
- **REDIS_URI**: Connection string Redis

### GPU Support

Để sử dụng GPU, cần:

1. **Cài đặt NVIDIA Container Toolkit**:
```bash
# Ubuntu/Debian
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

2. **Uncomment GPU config** trong `docker-compose.yml`:
```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

3. **Kiểm tra GPU**:
```bash
docker-compose exec ragflow_app nvidia-smi
```

### Ollama Setup (Nếu dùng local LLM)

1. **Pull model** (sau khi Ollama container đã chạy):
```bash
docker-compose exec ollama ollama pull llama3.2
```

2. **Kiểm tra models**:
```bash
docker-compose exec ollama ollama list
```

3. **Uncomment Ollama dependency** trong `docker-compose.yml`:
```yaml
depends_on:
  ollama:
    condition: service_healthy
```

## Services

### 1. MongoDB
- **Port**: 27017
- **Data**: Persistent volume `mongodb_data`
- **Default credentials**: admin/password (thay đổi trong .env)

### 2. Redis
- **Port**: 6379
- **Data**: Persistent volume `redis_data`
- **Password**: Set trong .env (REDIS_PASSWORD)

### 3. Ollama (Optional)
- **Port**: 11434
- **Data**: Persistent volume `ollama_data`
- **Models**: Lưu trong volume

### 4. RAG Flow App
- **Port**: 8000
- **API Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/health

## Commands

### Quản lý containers

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart services
docker-compose restart

# Stop và xóa volumes (mất data)
docker-compose down -v

# Rebuild image
docker-compose build --no-cache ragflow_app

# View logs
docker-compose logs -f [service_name]

# Execute command trong container
docker-compose exec ragflow_app bash
```

### Database Management

```bash
# MongoDB shell
docker-compose exec mongodb mongosh -u admin -p password

# Redis CLI
docker-compose exec redis redis-cli -a password

# Backup MongoDB
docker-compose exec mongodb mongodump --out /backup
docker cp ragflow_mongodb:/backup ./backup

# Backup Redis
docker-compose exec redis redis-cli -a password SAVE
```

## Troubleshooting

### 1. GPU không hoạt động

```bash
# Kiểm tra NVIDIA Docker
docker run --rm --gpus all nvidia/cuda:12.6.0-base-ubuntu22.04 nvidia-smi

# Kiểm tra trong container
docker-compose exec ragflow_app nvidia-smi
```

### 2. Out of Memory

- Giảm batch size trong code
- Sử dụng OpenAI API thay vì Ollama local
- Tăng swap space

### 3. Port conflicts

Thay đổi ports trong `docker-compose.yml`:
```yaml
ports:
  - "8001:8000"  # Thay vì 8000:8000
```

### 4. Model download chậm

- Pre-download models vào volume `model_cache`
- Hoặc mount local cache folder:
```yaml
volumes:
  - ~/.cache/huggingface:/app/models
```

### 5. Connection errors

- Kiểm tra network: `docker network ls`
- Kiểm tra service names trong .env
- Đảm bảo services đã healthy: `docker-compose ps`

## Monitoring

### Resource Usage

```bash
# CPU, RAM usage
docker stats

# Disk usage
docker system df
```

### Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f ragflow_app

# Last 100 lines
docker-compose logs --tail=100 ragflow_app
```

## Security

### Production Checklist

- [ ] Thay đổi MongoDB password
- [ ] Thay đổi Redis password
- [ ] Sử dụng secrets management (Docker Secrets)
- [ ] Enable MongoDB authentication
- [ ] Setup firewall rules
- [ ] Use HTTPS (reverse proxy)
- [ ] Regular backups

### Example với secrets

```yaml
secrets:
  mongodb_password:
    file: ./secrets/mongodb_password.txt
  redis_password:
    file: ./secrets/redis_password.txt

services:
  mongodb:
    environment:
      MONGO_INITDB_ROOT_PASSWORD_FILE: /run/secrets/mongodb_password
    secrets:
      - mongodb_password
```

## Production Deployment

### 1. Sử dụng reverse proxy (Nginx)

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 2. Scale services

```bash
# Scale app instances
docker-compose up -d --scale ragflow_app=3
```

### 3. Health checks

```bash
# Monitor health
watch -n 5 'curl -s http://localhost:8000/health | jq'
```

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/)
- [Docker Compose Reference](https://docs.docker.com/compose/compose-file/)

