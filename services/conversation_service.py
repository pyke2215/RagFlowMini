# services/conversation_service.py
from datetime import datetime
import uuid
import os
from functools import lru_cache
from utils.mongodb_conn import get_mongodb_connection
from models import Conversation, Message


class ConversationService:
    def __init__(self):
        self.mongodb_connection = get_mongodb_connection()
        self.db = self.mongodb_connection.get_database(os.getenv("MONGODB_DATABASE", "StreetBooks_DB"))
    
    async def create_conversation(self, user_id: str, title: str = None) -> str:
        conversation_id = str(uuid.uuid4())
        conversation = Conversation(
            conversation_id=conversation_id,
            user_id=user_id,
            title=title or f"Conversation {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            message_count=0,
            metadata={}
        )
        await self.db.conversations.insert_one(conversation.model_dump())

        return conversation_id
    
    async def add_message(self, conversation_id: str, role: str, content: str, embedding_id: str = None, redis_cache=None):
        """
        Add message vào MongoDB và cache vào Redis ngay lập tức.
        Redis là source of truth cho chat, MongoDB là persistence.
        """
        message_id = str(uuid.uuid4())
        timestamp = datetime.now()
        message = Message(
            message_id=message_id,
            conversation_id=conversation_id,
            role=role,
            content=content,
            timestamp=timestamp,
            embedding_id=embedding_id,
            metadata={}
        )
        
        await self.db.messages.insert_one(message.model_dump())
        
        await self.db.conversations.update_one(
            {"conversation_id": conversation_id},
            {"$inc": {"message_count": 1}, "$set": {"updated_at": timestamp}}
        )
        
        if redis_cache:
            try:
                message_dict = {
                    "message_id": message_id,
                    "conversation_id": conversation_id,
                    "role": role,
                    "content": content,
                    "timestamp": timestamp.isoformat(),
                    "embedding_id": embedding_id,
                    "metadata": {}
                }
                redis_cache.add_message_to_conversation_cache(conversation_id, message_dict)
            except Exception as e:
                print(f"[ConversationService] Redis cache error: {e}")
        
        return message_id
    
    async def get_recent_messages(self, conversation_id: str, limit: int = 2) -> list:
        cursor = self.db.messages.find(
            {"conversation_id": conversation_id}
        ).sort("timestamp", -1).limit(limit)
        messages = await cursor.to_list(length=limit)
        return [dict(msg) for msg in reversed(messages)]


@lru_cache(maxsize=1)
def get_conversation_service() -> ConversationService:
    """
    FastAPI dependency factory that returns a singleton ConversationService instance.
    """
    return ConversationService()