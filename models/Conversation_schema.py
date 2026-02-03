# models/conversation.py
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from bson import ObjectId

class Conversation(BaseModel):
    conversation_id: str
    user_id: str
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    message_count: int = 0
    metadata: dict = {}