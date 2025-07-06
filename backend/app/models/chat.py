from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class ChatMessage(BaseModel):
    role: str = Field(..., description="Role of the message sender (user/assistant)")
    content: str = Field(..., description="Content of the message")
    timestamp: datetime = Field(default_factory=datetime.now)

class ChatRequest(BaseModel):
    video_id: str = Field(..., description="ID of the video to chat about")
    question: str = Field(..., description="User's question")
    conversation_history: Optional[List[ChatMessage]] = Field(default=[], description="Previous conversation messages")

class ChatBody(BaseModel):
    question: str = Field(..., description="User's question")
    conversation_history: Optional[List[ChatMessage]] = Field(default=[], description="Previous conversation messages")

class RelevantChunk(BaseModel):
    chunk_id: str = Field(..., description="ID of the relevant chunk")
    text: str = Field(..., description="Text content of the chunk")
    start_time: float = Field(..., description="Start timestamp in seconds")
    end_time: float = Field(..., description="End timestamp in seconds")
    relevance_score: float = Field(..., description="Relevance score (0-1)")
    formatted_timestamp: str = Field(..., description="Human-readable timestamp (e.g., '1:23:45')")

class ChatResponse(BaseModel):
    answer: str = Field(..., description="AI-generated answer")
    relevant_chunks: List[RelevantChunk] = Field(..., description="Source chunks used to generate the answer")
    video_id: str = Field(..., description="ID of the video being discussed")
    confidence_score: float = Field(..., description="Confidence in the answer (0-1)")
    processing_time: float = Field(..., description="Time taken to process the request in seconds")

class ConversationSession(BaseModel):
    session_id: str = Field(..., description="Unique session identifier")
    video_id: str = Field(..., description="ID of the video being discussed")
    messages: List[ChatMessage] = Field(default=[], description="All messages in the conversation")
    created_at: datetime = Field(default_factory=datetime.now)
    last_activity: datetime = Field(default_factory=datetime.now)

class ChatHistoryResponse(BaseModel):
    sessions: List[ConversationSession]
    total: int 