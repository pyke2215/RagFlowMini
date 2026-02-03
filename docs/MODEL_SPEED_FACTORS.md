# Các Yếu Tố Ảnh Hưởng Đến Tốc Độ Model

## Câu Hỏi: Tốc độ model có phụ thuộc vào chính model không?

**Trả lời: CÓ** - Tốc độ phụ thuộc vào **CẢ model VÀ prompt**, nhưng **model là yếu tố quan trọng nhất**.

---

## 1. Yếu Tố Model (Ảnh Hưởng Lớn Nhất) 🔥

### 1.1. Kích Thước Model
- **Model nhỏ** (7B params): ~10-50 tokens/giây
- **Model vừa** (13B params): ~5-20 tokens/giây  
- **Model lớn** (70B params): ~1-5 tokens/giây

**Ví dụ trong code:**
- `llama3.2` (3B) → Nhanh
- `llama3.1:70b` → Chậm hơn 20-30 lần

### 1.2. Kiến Trúc Model
- **Encoder-only** (BERT, BGE-M3): Nhanh, xử lý song song
- **Decoder-only** (GPT, Llama): Chậm hơn, generate tuần tự
- **Encoder-Decoder** (T5, BART): Trung bình

**Trong code hiện tại:**
```python
# Embedding model (encoder-only) - NHANH
embedding_service.encode_single(query)  # ~50-200ms

# LLM (decoder-only) - CHẬM HƠN
llm_service.generate(messages)  # ~1-10 giây
```

### 1.3. Tối Ưu Hóa Model
- **Full precision** (FP32): Chậm nhất, chính xác nhất
- **Half precision** (FP16): Nhanh hơn 2x, giảm VRAM 50%
- **Quantization** (Q4, Q8): Nhanh hơn 3-5x, giảm VRAM 75-90%

**Ví dụ Ollama:**
```bash
ollama run llama3.2        # FP16, ~2GB VRAM
ollama run llama3.2:q4_0   # Q4, ~1GB VRAM, nhanh hơn 2-3x
```

---

## 2. Yếu Tố Prompt (Ảnh Hưởng Trung Bình)

### 2.1. Độ Dài Prompt
- **Prompt ngắn** (100 tokens): Xử lý nhanh
- **Prompt dài** (2000 tokens): Xử lý chậm hơn 20x

**Trong code:**
```python
# Prompt ngắn
query = "What is AI?"  # ~5 tokens → Nhanh

# Prompt dài (có context)
context_text = "...1000 words..."  # ~250 tokens → Chậm hơn
```

### 2.2. Độ Phức Tạp
- **Câu hỏi đơn giản**: "What is X?" → Nhanh
- **Câu hỏi phức tạp**: "Explain X, compare with Y, analyze Z..." → Chậm hơn

### 2.3. Số Lượng Context
- **Không có context**: Nhanh nhất
- **5 contexts** (top_k=5): Chậm hơn ~2-3x
- **20 contexts**: Chậm hơn ~5-10x

---

## 3. Yếu Tố Hardware (Ảnh Hưởng Lớn) 💻

### 3.1. GPU vs CPU
- **GPU (CUDA)**: Nhanh hơn CPU 10-100x
- **CPU**: Chậm, chỉ dùng khi không có GPU

**Trong code:**
```python
# Embedding service
device = os.getenv("EMBEDDING_DEVICE", "cuda")  # GPU → Nhanh
# CPU → Chậm hơn 50-100x
```

### 3.2. VRAM (Video RAM)
- **Đủ VRAM**: Model load vào GPU → Nhanh
- **Thiếu VRAM**: Model swap ra RAM → Chậm 10-50x

**Ví dụ:**
- `llama3.2` cần ~2GB VRAM
- `llama3.1:70b` cần ~40GB VRAM

---

## 4. Yếu Tố Cấu Hình (Ảnh Hưởng Nhỏ)

### 4.1. Max Tokens
```python
max_tokens=1024  # Generate 1024 tokens → Chậm
max_tokens=256   # Generate 256 tokens → Nhanh hơn 4x
```

### 4.2. Temperature
- `temperature=0.1`: Deterministic, nhanh hơn một chút
- `temperature=0.9`: Random, chậm hơn một chút (khác biệt nhỏ)

---

## 5. So Sánh Thực Tế Trong Code

### 5.1. Embedding Service (BGE-M3)
```python
# Model: BAAI/bge-m3 (encoder-only, ~560M params)
# Device: CUDA
# Tốc độ: ~50-200ms cho 1 query
query_embedding = embedding_service.encode_single(query)
```

**Tại sao nhanh?**
- Encoder-only: Xử lý song song toàn bộ input
- Model nhỏ: 560M params
- GPU: Tận dụng CUDA cores

### 5.2. LLM Service (Llama3.2)
```python
# Model: llama3.2 (decoder-only, ~3B params)
# Device: Ollama (có thể GPU hoặc CPU)
# Tốc độ: ~1-10 giây cho 1 response
response = await llm_service.generate(messages, max_tokens=1024)
```

**Tại sao chậm hơn?**
- Decoder-only: Generate từng token tuần tự
- Phải xử lý toàn bộ prompt trước khi generate
- Output length: 1024 tokens = 1024 lần forward pass

---

## 6. Benchmark Tham Khảo

### 6.1. Embedding Models (tokens/giây)
| Model | Size | GPU | CPU |
|-------|------|-----|-----|
| BGE-M3 | 560M | ~500-1000 | ~50-100 |
| BGE-Large | 326M | ~800-1500 | ~80-150 |

### 6.2. LLM Models (tokens/giây)
| Model | Size | GPU (RTX 3090) | CPU |
|-------|------|----------------|-----|
| Llama3.2 | 3B | ~50-100 | ~2-5 |
| Llama3.1 | 8B | ~20-40 | ~1-2 |
| Llama3.1:70b | 70B | ~5-10 | Không chạy được |

---

## 7. Tối Ưu Hóa Tốc Độ

### 7.1. Chọn Model Phù Hợp
```bash
# Nhanh, chất lượng tốt
ollama run llama3.2

# Nhanh hơn, chất lượng giảm nhẹ
ollama run llama3.2:q4_0
```

### 7.2. Giảm Prompt Length
```python
# Thay vì top_k=20
contexts = await rag_service.retrieve_context(query, top_k=5)  # Nhanh hơn
```

### 7.3. Giảm Max Tokens
```python
# Thay vì max_tokens=2048
response = await llm_service.generate(messages, max_tokens=512)  # Nhanh hơn 4x
```

### 7.4. Cache Embeddings
```python
# Đã implement trong code
redis_cache.cache_query_embedding(query, embedding)  # Tránh embed lại
```

---

## 8. Kết Luận

**Tốc độ model phụ thuộc vào:**

1. **Model (70%)**: Kích thước, kiến trúc, tối ưu hóa
2. **Hardware (20%)**: GPU vs CPU, VRAM
3. **Prompt (8%)**: Độ dài, độ phức tạp
4. **Cấu hình (2%)**: Max tokens, temperature

**Trong code hiện tại:**
- Embedding: Nhanh (~50-200ms) - Model nhỏ, encoder-only, GPU
- LLM: Chậm hơn (~1-10s) - Decoder-only, generate tuần tự
- Đã có cache cho embeddings
- Có thể tối ưu: Giảm `max_tokens`, dùng quantization, giảm `top_k`

