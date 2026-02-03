# Đánh giá Cache Strategy: Messages vs Embeddings

## 1. Cache Messages trong Redis

### Ưu điểm:
- **Đơn giản**: Chỉ cache text messages, không cần xử lý phức tạp
- **Hiệu quả cho conversation context**: Lấy ngay 2 messages gần nhất, không cần query MongoDB
- **Memory nhẹ**: Mỗi message chỉ vài KB text
- **Dễ debug**: Có thể xem trực tiếp messages trong Redis
- **Phù hợp với use case**: Chat cần conversation history, không cần embedding của history

### Nhược điểm:
- **Không tối ưu cho retrieval**: Nếu muốn search trong conversation history thì vẫn phải embed lại
- **TTL cần quản lý**: Messages cũ có thể bị expire

### Khi nào dùng:
- **Chat với RAG**: Chỉ cần 2 messages gần nhất làm context cho LLM
- **Conversation flow**: Messages được dùng trực tiếp trong prompt, không cần search

---

## 2. Cache Embeddings trong Redis

### Ưu điểm:
- **Tối ưu cho retrieval**: Nếu muốn search trong conversation history, không cần embed lại
- **Tái sử dụng**: Cùng một query sẽ không embed lại
- **Hiệu quả cho similarity search**: Có thể dùng embeddings để tìm messages tương tự

### Nhược điểm:
- **Memory nặng hơn**: Mỗi embedding vector có thể 384-1024 dimensions (float32) = 1.5-4KB
- **Phức tạp hơn**: Cần quản lý cả messages và embeddings
- **Không cần thiết cho chat đơn giản**: Chat chỉ cần text, không cần search

### Khi nào dùng:
- **Semantic search trong history**: Muốn tìm messages có nghĩa tương tự
- **Query caching**: Cache embeddings của user queries để tránh embed lại
- **Hybrid search**: Kết hợp keyword + semantic search

---

## 3. So sánh cho use case hiện tại

### Use case: Chat với RAG
- **Input**: User query + 2 messages gần nhất
- **Flow**: 
  1. Embed query → Search ChromaDB
  2. Lấy 2 messages gần nhất → Đưa vào LLM prompt
  3. Generate response

### Khuyến nghị:

#### **Cache Messages (Ưu tiên cao)**
- **Cần thiết**: Lấy 2 messages gần nhất từ Redis thay vì MongoDB
- **Hiệu quả**: Giảm MongoDB query từ mỗi request
- **Đơn giản**: Chỉ cache text, dùng trực tiếp trong prompt

#### **Cache Query Embeddings (Ưu tiên trung bình)**
- **Hữu ích**: Nếu user hỏi lại cùng câu hỏi, không cần embed lại
- **Không bắt buộc**: Embedding query chỉ mất ~50-200ms, không phải bottleneck lớn nhất

#### **Cache Message Embeddings (Không cần)**
- **Không cần thiết**: Messages chỉ dùng làm context text, không search
- **Lãng phí memory**: Cache embeddings của messages mà không dùng

---

## 4. Kết luận

### Cho use case hiện tại (Chat với RAG):

**Cache Messages trong Redis** là lựa chọn tốt nhất:
- Giảm MongoDB queries
- Đơn giản, hiệu quả
- Phù hợp với flow hiện tại

**Cache Query Embeddings** là tối ưu bổ sung:
- Tránh embed lại cùng query
- Memory overhead thấp (chỉ cache queries, không cache tất cả messages)

**Không cache Message Embeddings**:
- Không cần thiết vì không search trong history
- Lãng phí memory

---

## 5. Implementation hiện tại (Đã triển khai)

### Đã implement:
1. **Cache Messages trong Redis**: 
   - `cache_conversation_messages()`: Cache list messages
   - `get_conversation_messages(limit=2)`: Lấy N messages gần nhất từ Redis
   - `add_message_to_conversation_cache()`: Thêm message mới vào cache
   - Auto-limit: Giữ tối đa 50 messages trong cache

2. **Cache Query Embeddings**: 
   - `cache_query_embedding()`: Cache embedding của query
   - Check cache trước khi embed (trong `retrieve_context`)
   - TTL: 1800s (30 phút)

3. **Auto-cache khi add message**: 
   - `add_message()` tự động cache vào Redis ngay sau khi save MongoDB
   - Messages được append vào list trong Redis
   - MongoDB chỉ dùng cho persistence

### Flow hiện tại (Đã triển khai):

```
┌─────────────────────────────────────────────────────────┐
│  POST /chat/query                                       │
└─────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────┐
│  1. Rate Limiting (Redis)                               │
│     - Check user rate limit                             │
└─────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────┐
│  2. Get Recent Messages (Redis ưu tiên)                │
│     Lấy từ Redis: get_conversation_messages(limit=2)│
│     Nếu không có → MongoDB → Cache vào Redis       │
└─────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────┐
│  3. Retrieve Context từ ChromaDB                       │
│     a) Check cache query embedding (Redis)              │
│     b) Embed query (nếu chưa cache)                     │
│     c) Search ChromaDB với embedding                     │
│     d) Cache query embedding (nếu mới)                  │
└─────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────┐
│  4. Generate Response với LLM                           │
│     - Build prompt: System + Context + History + Query  │
│     - Call LLM (Ollama/OpenAI)                          │
└─────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────┐
│  5. Save Messages (MongoDB + Redis)                     │
│     a) Save user message → MongoDB                       │
│        → Auto-cache vào Redis ngay                       │
│     b) Save assistant message → MongoDB                 │
│        → Auto-cache vào Redis ngay                       │
└─────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────┐
│  Response với timings                                   │
└─────────────────────────────────────────────────────────┘
```

### Chi tiết từng bước:

#### **Bước 1: Rate Limiting**
- Redis key: `ratelimit:{user_id}`
- Window: 60s, Limit: 20 requests

#### **Bước 2: Get Recent Messages**
```python
# Ưu tiên Redis
recent_messages = redis.get_conversation_messages(conversation_id, limit=2)

# Fallback MongoDB (chỉ khi cache miss)
if not recent_messages:
    recent_messages = await mongo.get_recent_messages(conversation_id, limit=2)
    redis.cache_conversation_messages(conversation_id, recent_messages)
```

#### **Bước 3: Retrieve Context**
```python
# Check cache embedding
cached_embedding = redis.get(f"embed:query:{hash(query)}")

if cached_embedding:
    query_embedding = cached_embedding  # Skip embedding
else:
    query_embedding = embedding_service.encode(query)  # Embed
    redis.cache_query_embedding(query, query_embedding)  # Cache

# Search ChromaDB
contexts = chroma_db.query(query_embedding, top_k=5)
```

#### **Bước 4: Generate Response**
```python
messages = [
    {"role": "system", "content": system_prompt},
    ...recent_messages...,  # Từ Redis
    {"role": "user", "content": query_with_context}
]
response = llm_service.generate(messages)
```

#### **Bước 5: Save Messages**
```python
# Save + Cache cùng lúc
user_msg_id = await conv_service.add_message(
    conversation_id, "user", query,
    redis_cache=redis  # Auto-cache vào Redis
)

assistant_msg_id = await conv_service.add_message(
    conversation_id, "assistant", response,
    redis_cache=redis  # Auto-cache vào Redis
)
```

### Redis Keys Structure:
```
conv:{conversation_id}:messages     → List of messages (JSON array)
embed:query:{hash(query)}          → Query embedding (JSON array)
ratelimit:{user_id}                → Rate limit counter
```

### Performance Benefits:
- **MongoDB queries**: Giảm từ mỗi request → chỉ khi cache miss
- **Embedding time**: Giảm khi query trùng lặp (cache hit)
- **Response time**: Nhanh hơn 50-200ms nhờ Redis cache

---

## 6. Tối ưu thêm có thể làm:

1. **Batch cache**: Cache nhiều messages cùng lúc khi load từ MongoDB
2. **TTL thông minh**: Tăng TTL cho conversations đang active
3. **Memory limit**: Giới hạn số messages cache (đã có `max_messages=50`)
4. **Pre-warm**: Cache conversations phổ biến khi app start

