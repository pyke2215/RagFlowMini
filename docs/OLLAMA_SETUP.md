# Hướng dẫn Setup Ollama với Llama 3.2

## 1. Cài đặt Ollama

### Windows:
1. Download từ: https://ollama.com/download
2. Chạy installer
3. Ollama sẽ tự động chạy ở background trên port `11434`

### Ubuntu/Docker:
```bash
# Cách 1: Cài trực tiếp
curl -fsSL https://ollama.com/install.sh | sh

# Cách 2: Docker (khuyến nghị cho production)
docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama
```

## 2. Pull Model Llama 3.2

```bash
# Pull model (sẽ tự động download)
ollama pull llama3.2

# Hoặc các biến thể khác:
ollama pull llama3.2:1b      # 1B parameters (nhẹ nhất)
ollama pull llama3.2:3b      # 3B parameters
ollama pull llama3.2:8b      # 8B parameters (cân bằng)
ollama pull llama3.2:70b     # 70B parameters (mạnh nhất, cần GPU)
```

## 3. Kiểm tra Ollama đang chạy

```bash
# Test API
curl http://localhost:11434/api/tags

# Hoặc test chat
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2",
  "prompt": "Hello, how are you?",
  "stream": false
}'
```

## 4. Cấu hình trong .env

```env
# LLM Configuration cho Ollama
LLM_PROVIDER=ollama
LLM_MODEL=llama3.2
LLM_BASE_URL=http://localhost:11434/v1
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000
```

## 5. Nếu host trên Ubuntu server khác

```env
# Thay localhost bằng IP server
LLM_BASE_URL=http://192.168.1.100:11434/v1
```

## 6. Docker Compose (nếu muốn chạy cùng với app)

Tạo file `docker-compose.yml`:

```yaml
version: '3.8'

services:
  ollama:
    image: ollama/ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    # Nếu có GPU
    # deploy:
    #   resources:
    #     reservations:
    #       devices:
    #         - driver: nvidia
    #           count: 1
    #           capabilities: [gpu]

volumes:
  ollama_data:
```

Chạy:
```bash
docker-compose up -d
```

## Lưu ý:

- **Không cần SentenceTransformer** cho Ollama (chỉ dùng cho embedding)
- Ollama có API tương thích OpenAI, code hiện tại đã hỗ trợ sẵn
- Model sẽ được cache ở `~/.ollama/models/` (Linux) hoặc `C:\Users\<user>\.ollama\models\` (Windows)
- Nếu có GPU, Ollama sẽ tự động dùng GPU để tăng tốc

