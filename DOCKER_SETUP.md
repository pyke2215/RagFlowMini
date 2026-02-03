# Docker Setup Guide - RAG Flow Mini

Hướng dẫn nhanh để setup và chạy RAG Flow Mini với Docker.

## Yêu Cầu

- **Docker** 20.10+ và **Docker Compose** 2.0+
- **NVIDIA Docker** (nếu dùng GPU) - [Hướng dẫn cài đặt](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)
- **NVIDIA GPU** với CUDA 12.6+ (khuyến nghị)

## Quick Start

### 1. Chuẩn bị file cấu hình

```bash
# Copy file env.example thành .env
cp env.example .env

# Chỉnh sửa .env với cấu hình của bạn
# Quan trọng: Thay đổi passwords cho MongoDB và Redis
```

### 2. Chạy với Docker Compose

```bash
# Chạy từ thư mục docker
cd docker

# Build và start tất cả services
docker-compose up -d

# Hoặc sử dụng script (Linux/Mac)
./start.sh
```

### 3. Kiểm tra

```bash
# Check health
curl http://localhost:8000/health

# Mở API docs
# http://localhost:8000/docs
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| **ragflow_app** | 8000 | Main application |
| **mongodb** | 27017 | MongoDB database |
| **redis** | 6379 | Redis cache |
| **ollama** | 11434 | Ollama LLM (optional) |

## Cấu Hình

### File `.env`

Chỉnh sửa các biến quan trọng:

```env
# LLM Configuration
LLM_PROVIDER=ollama  # hoặc openai
LLM_BASE_URL=http://ollama:11434/v1

# MongoDB
MONGODB_URI=mongodb://admin:YOUR_PASSWORD@mongodb:27017/rag_db?authSource=admin

# Redis
REDIS_URI=redis://:YOUR_PASSWORD@redis:6379/0
```

### GPU Support

1. **Cài NVIDIA Container Toolkit**:
```bash
# Ubuntu/Debian
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

2. **Kiểm tra GPU**:
```bash
docker-compose exec ragflow_app nvidia-smi
```

### Ollama Setup (Nếu dùng local LLM)

```bash
# Pull model sau khi Ollama đã chạy
docker-compose exec ollama ollama pull llama3.2

# List models
docker-compose exec ollama ollama list
```

## Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f ragflow_app

# Rebuild
docker-compose build --no-cache ragflow_app

# Restart
docker-compose restart ragflow_app

# Execute command
docker-compose exec ragflow_app bash
```

## Troubleshooting

### GPU không hoạt động
```bash
# Test NVIDIA Docker
docker run --rm --gpus all nvidia/cuda:12.6.0-base-ubuntu22.04 nvidia-smi

# Check trong container
docker-compose exec ragflow_app nvidia-smi
```

### Port conflicts
Thay đổi ports trong `docker-compose.yml`:
```yaml
ports:
  - "8001:8000"  # Thay vì 8000:8000
```

### Connection errors
- Kiểm tra service names trong `.env` phải khớp với `docker-compose.yml`
- Đảm bảo services đã healthy: `docker-compose ps`

### Out of Memory
- Giảm batch size trong code
- Sử dụng OpenAI API thay vì Ollama local
- Tăng swap space

## Monitoring

```bash
# Resource usage
docker stats

# Service status
docker-compose ps

# Logs
docker-compose logs -f
```

## Security (Production)

- [ ] Thay đổi MongoDB password
- [ ] Thay đổi Redis password  
- [ ] Sử dụng Docker Secrets
- [ ] Enable MongoDB authentication
- [ ] Setup firewall
- [ ] Use HTTPS (reverse proxy)

## Xem thêm

Chi tiết đầy đủ: [docker/README.md](docker/README.md)

