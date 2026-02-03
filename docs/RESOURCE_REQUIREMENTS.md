# Tóm Tắt Cấu Hình Tài Nguyên - RAG Flow Mini

## Tổng Quan Hệ Thống

Hệ thống RAG Flow Mini bao gồm các thành phần chính:
- **Embedding Service**: Model BAAI/bge-m3 để tạo embeddings
- **LLM Service**: Ollama (local) hoặc OpenAI API
- **Vector Database**: ChromaDB (local storage)
- **NoSQL Database**: MongoDB (conversations, messages)
- **Cache Layer**: Redis (conversations, embeddings, rate limiting)
- **Web Framework**: FastAPI + Uvicorn

---

## Tài Nguyên Tối Thiểu (Minimum)

### RAM
- **Tối thiểu**: 8GB
- **Khuyến nghị**: 16GB
- **Phân bổ**:
  - Embedding Model (BAAI/bge-m3): ~2-3GB
  - LLM (Ollama qwen3-vl:8b): ~8-10GB
  - MongoDB: ~500MB-1GB
  - Redis: ~200-500MB
  - Python runtime + dependencies: ~1-2GB
  - ChromaDB: ~100-500MB (tùy số lượng documents)

### GPU
- **Bắt buộc**: NVIDIA GPU với CUDA support 12
- **VRAM tối thiểu**: 6GB (chỉ embedding model)
- **VRAM khuyến nghị**: 12GB+ (embedding + LLM local)
- **Model**: 
  - Embedding: BAAI/bge-m3 (~1-2GB VRAM)
  - LLM (nếu dùng Ollama local): qwen3-vl:8b (~8-10GB VRAM)

### Storage
- **Tối thiểu**: 20GB free space
- **Phân bổ**:
  - Model cache (HuggingFace): ~5-10GB
  - ChromaDB database: ~1-5GB (tùy số documents)
  - MongoDB data: ~500MB-2GB (tùy số conversations)
  - Redis data: ~100MB-1GB
  - Python packages: ~2-3GB
  - Temporary uploads: ~1GB

### CPU
- **Tối thiểu**: 4 cores
- **Khuyến nghị**: 8+ cores
- **Lưu ý**: Nếu không có GPU, CPU sẽ phải xử lý embedding (rất chậm)

---

## Tài Nguyên Khuyến Nghị (Recommended)

### RAM
- **Khuyến nghị**: 32GB
- **Lý do**: 
  - Để chạy cả embedding model và LLM cùng lúc
  - Xử lý nhiều requests đồng thời
  - Cache embeddings và conversations

### GPU
- **VRAM**: 16GB+ (NVIDIA RTX 3090, RTX 4090, hoặc A100)
- **Lý do**: 
  - Chạy embedding model và LLM cùng lúc
  - Batch processing khi ingest files
  - Xử lý nhiều requests song song

### Storage
- **Khuyến nghị**: 50GB+ SSD
- **Lý do**:
  - Lưu trữ nhiều collections trong ChromaDB
  - Cache models và embeddings
  - Logs và temporary files

### CPU
- **Khuyến nghị**: 12+ cores
- **Lý do**: Xử lý I/O, database queries, và preprocessing

---

## Tài Nguyên Cho Production

### RAM
- **Production**: 64GB+
- **Phân bổ**:
  - Embedding service: 4-6GB
  - LLM service (nếu local): 16-32GB
  - MongoDB: 4-8GB
  - Redis: 2-4GB
  - Application: 2-4GB
  - Buffer: 10-20GB

### GPU
- **Production**: 24GB+ VRAM (A100 40GB, RTX 4090 24GB)
- **Hoặc**: Multiple GPUs với model sharding

### Storage
- **Production**: 200GB+ SSD (NVMe preferred)
- **Backup**: Thêm 200GB+ cho backups

### Network
- **Bandwidth**: 100Mbps+ (nếu dùng OpenAI API)
- **Latency**: <50ms đến MongoDB và Redis

---

## Cấu Hình Chi Tiết Theo Component

### 1. Embedding Service (BAAI/bge-m3)
```
Model Size: ~1.5GB (download)
VRAM Usage: ~1-2GB khi inference
RAM Usage: ~2-3GB (model + activations)
Batch Size: 64 (có thể tăng nếu có nhiều VRAM)
```

### 2. LLM Service
#### Option A: Ollama (Local)
```
Model: qwen3-vl:8b
VRAM Usage: ~8-10GB
RAM Usage: ~10-12GB
Inference Speed: Phụ thuộc GPU
```

#### Option B: OpenAI API
```
VRAM Usage: 0GB (chạy trên cloud)
RAM Usage: ~100MB (chỉ client)
Cost: Pay-per-use
Latency: Phụ thuộc network
```

### 3. ChromaDB
```
Storage: ~1-5GB cho 100K documents
RAM: ~500MB-2GB (tùy collection size)
Index: In-memory hoặc on-disk
```

### 4. MongoDB
```
Storage: ~500MB-2GB cho 10K conversations
RAM: ~1-4GB (working set)
Connections: 50-100 concurrent
```

### 5. Redis
```
Storage: ~100MB-1GB (tùy cache size)
RAM: ~200MB-2GB
TTL: 3600s (1 hour) cho conversations
```

---

## Tối Ưu Hóa Tài Nguyên

### 1. Giảm RAM Usage
- Sử dụng OpenAI API thay vì Ollama local
- Giảm batch size trong embedding
- Giới hạn số lượng contexts retrieve (top_k)
- Tắt các service không cần thiết

### 2. Giảm VRAM Usage
- Quantize models (8-bit, 4-bit)
- Sử dụng model nhỏ hơn
- Offload một phần model sang CPU
- Dùng OpenAI API thay vì local LLM

### 3. Giảm Storage
- Xóa model cache không dùng
- Compress ChromaDB collections
- Archive old conversations
- Clean temporary files định kỳ

### 4. Tăng Performance
- Sử dụng GPU mạnh hơn
- Tăng batch size
- Cache embeddings trong Redis
- Optimize database queries

---

## Checklist Cấu Hình

### Minimum Setup
- [ ] 8GB RAM
- [ ] NVIDIA GPU 6GB VRAM
- [ ] 20GB storage
- [ ] MongoDB installed
- [ ] Redis installed
- [ ] CUDA toolkit installed

### Recommended Setup
- [ ] 32GB RAM
- [ ] NVIDIA GPU 16GB VRAM
- [ ] 50GB SSD storage
- [ ] MongoDB với replication
- [ ] Redis với persistence
- [ ] CUDA 12.6+

### Production Setup
- [ ] 64GB+ RAM
- [ ] NVIDIA GPU 24GB+ VRAM hoặc multiple GPUs
- [ ] 200GB+ NVMe SSD
- [ ] MongoDB cluster
- [ ] Redis cluster
- [ ] Load balancer
- [ ] Monitoring tools

---

## Monitoring Tài Nguyên

### Metrics Cần Theo Dõi
1. **GPU Utilization**: Nên >70% khi có requests
2. **VRAM Usage**: Không vượt quá 90%
3. **RAM Usage**: Không vượt quá 80%
4. **Disk I/O**: ChromaDB và MongoDB
5. **Network Latency**: Nếu dùng OpenAI API
6. **Request Latency**: P50, P95, P99

### Tools Khuyến Nghị
- `nvidia-smi` cho GPU monitoring
- `htop` hoặc `top` cho CPU/RAM
- `iostat` cho disk I/O
- MongoDB Compass cho database
- Redis CLI cho cache
- Prometheus + Grafana cho production

---

## Lưu Ý Quan Trọng

1. **GPU là bắt buộc** cho embedding model, không thể chạy ổn định trên CPU
2. **Redis và MongoDB** nên chạy trên cùng server để giảm latency
3. **ChromaDB** lưu trên disk, nên dùng SSD để tăng tốc
4. **Batch size** có thể điều chỉnh trong code để phù hợp với VRAM
5. **Rate limiting** đã được implement (20 requests/phút/user)

---

## Hỗ Trợ

Nếu gặp vấn đề về tài nguyên:
1. Kiểm tra logs trong console
2. Monitor GPU/CPU/RAM usage
3. Giảm batch size hoặc top_k
4. Sử dụng OpenAI API thay vì local LLM
5. Scale horizontally (multiple instances)

