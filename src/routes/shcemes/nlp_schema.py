from pydantic import BaseModel
from typing import Optional, List

class PushRequestSchema(BaseModel):
    do_reset : Optional[int] = 0

class ChatMessage(BaseModel):
    role: str           # "system" | "user" | "assistant"
    content: str

class SearchRequestSchema(BaseModel):
    text: str
    limit: Optional[int] = 10
    chat_history: Optional[List[ChatMessage]] = []