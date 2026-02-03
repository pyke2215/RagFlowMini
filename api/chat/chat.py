# api/chat.py
from fastapi import APIRouter, Form, HTTPException, Depends
from services.rag_service import get_rag_service
from services.conversation_service import get_conversation_service
from utils.redis_conn import get_redis_connection

router = APIRouter(prefix="/chat", tags=["chat"])

redis_connection = get_redis_connection()
conv_service = get_conversation_service()
rag_service = get_rag_service()

@router.post("/conversations")
async def create_conversation(
    user_id: str = Form(...),
    title: str = Form(None),
):
    """Tạo conversation mới"""
    conversation_id = await conv_service.create_conversation(user_id, title)
    return {"conversation_id": conversation_id, "status": "created"}

@router.post("/query")
async def chat(
    query: str = Form(...),
    conversation_id: str = Form(...),
    user_id: str = Form(...),
    collection_name: str = Form("default_collection"),
    top_k: int = Form(3),  # Số lượng contexts retrieve từ ChromaDB (mặc định: 5)
    isFollowUp: bool = Form(False),
):
    """Chat với RAG + context"""
    import time
    timings = {}
    start_total = time.perf_counter()
    
    # 1. Rate limiting
    t0 = time.perf_counter()
    if not redis_connection.check_rate_limit(user_id, limit=20, window=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    timings["rate_limit"] = (time.perf_counter() - t0) * 1000
    
    # 2. Get recent messages từ Redis (ưu tiên) - không query MongoDB
    # Chỉ lấy 1 previous user query gần nhất để làm context
    t0 = time.perf_counter()
    previous_queries = []
    if isFollowUp:
        recent_messages = redis_connection.get_conversation_messages(conversation_id, limit=None)
        if recent_messages is None:
            # Nếu không có trong Redis, lấy từ MongoDB (fallback - chỉ khi cache miss)
            recent_messages = await conv_service.get_recent_messages(conversation_id, limit=5)
            # Cache vào Redis để lần sau dùng
            if recent_messages:
                redis_connection.cache_conversation_messages(conversation_id, recent_messages)
        
        # Lọc chỉ lấy các câu hỏi của user (role="user"), bỏ qua câu trả lời (role="assistant")
        # Chỉ lấy 1 câu hỏi gần nhất (câu hỏi cuối cùng trong list)
        if recent_messages:
            user_queries = [
                msg.get("content", "") 
                for msg in recent_messages 
                if msg.get("role") == "user"
            ]
            # Chỉ lấy 1 câu hỏi gần nhất (câu hỏi cuối cùng)
            if user_queries:
                previous_queries = [user_queries[-1]]  # Chỉ lấy câu hỏi cuối cùng
                print(f"[Chat] Using 1 previous user query as context")
        
        timings["get_messages"] = (time.perf_counter() - t0) * 1000
        
    # 4+5. Decide dùng context hay không + generate response
    #    (gồm 1 bước classification + optional retrieve_context + generate_response)
    t0 = time.perf_counter()
    rag_result = await rag_service.decide_and_generate(
        query=query,
        collection_name=collection_name,
        top_k=top_k,
        redis_cache=redis_connection,
        previous_queries=previous_queries,  # Truyền previous queries vào
    )
    timings["rag_decide_and_generate"] = (time.perf_counter() - t0) * 1000

    response = rag_result["response"]
    options = rag_result.get("options", [])
    contexts = rag_result.get("contexts", [])
    
    # 6. Save messages to MongoDB (persistence) và cache vào Redis ngay lập tức
    t0 = time.perf_counter()
    
    # Save user message (tự động cache vào Redis trong add_message)
    user_msg_id = await conv_service.add_message(
        conversation_id=conversation_id,
        role="user",
        content=query,
        redis_cache=redis_connection
    )
    
    # Save assistant message (chỉ lưu response, không lưu options)
    # Options sẽ được trả về riêng trong API response
    assistant_msg_id = await conv_service.add_message(
        conversation_id=conversation_id,
        role="assistant",
        content=response,
        redis_cache=redis_connection
    )
    
    timings["save_messages"] = (time.perf_counter() - t0) * 1000
    
    timings["total"] = (time.perf_counter() - start_total) * 1000
    
    # Log timings
    print(f"\n[PERF] Request timings (ms):")
    for step, duration in timings.items():
        print(f"  {step}: {duration:.2f}ms")
    
    return {
        "conversation_id": conversation_id,
        "user_message_id": user_msg_id,
        "assistant_message_id": assistant_msg_id,
        "response": response,  # Chỉ phần Main Response, không có header
        "options": options,  # Mảng các câu hỏi/yêu cầu để làm button
        "contexts_used": [ctx["content"][:100] for ctx in contexts],
        "used_context": rag_result.get("used_context", False),
        "needs_context": rag_result.get("needs_context", None),
        "is_book_related": rag_result.get("is_book_related", None),
        "timings_ms": timings
    }

@router.get("/conversations/{conversation_id}/messages")
async def get_messages(
    conversation_id: str,
    limit: int = 50,
):
    """Lấy lịch sử messages của conversation"""
    cursor = conv_service.db.messages.find(
        {"conversation_id": conversation_id}
    ).sort("timestamp", -1).limit(limit)
    messages = await cursor.to_list(length=limit)
    return {"messages": [dict(msg) for msg in reversed(messages)]}