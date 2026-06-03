from pydantic import BaseModel
from typing import Optional

class PushRequestSchema(BaseModel):
    do_reset : Optional[int] = 0
    
class SearchRequestSchema(BaseModel):
    text: str
    limit: Optional[int] = 5