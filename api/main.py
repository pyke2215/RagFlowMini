from fastapi import FastAPI
from .Ingest.main import create_ingest_app
from .chat.chat import router as chat_router
from dotenv import load_dotenv
from utils.mongodb_conn import get_mongodb_connection
from utils.redis_conn import get_redis_connection
load_dotenv()
mongodb_conn = get_mongodb_connection()
redis_conn = get_redis_connection()
app = FastAPI(title="RAG Backend API")
# Mount ingest thành sub-app
ingest_app = create_ingest_app()
app.mount("/ingest-service", ingest_app)

app.include_router(chat_router)

@app.get("/health")
async def health():
    if not mongodb_conn.check_connection():
        return {"status": "error", "message": "MongoDB connection failed"}
    if not redis_conn.check_connection():
        return {"status": "error", "message": "Redis connection failed"}
    return {"status": "ok", "message": "RAG Backend is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)