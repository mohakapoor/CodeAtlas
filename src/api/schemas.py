from pydantic import BaseModel, Field
from typing import List, Optional

class ChatRequest(BaseModel):
    query: str = Field(..., description="The natural language question to ask CodeAtlas.")

class SourceModel(BaseModel):
    repo: str
    path: str
    type: str
    symbol: Optional[str] = None

class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceModel]
