# models/conversation.py
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from bson import ObjectId

class Message(BaseModel):
    message_id: str
    conversation_id: str
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime
    embedding_id: Optional[str] = None  # ID trong ChromaDB
    metadata: dict = {}