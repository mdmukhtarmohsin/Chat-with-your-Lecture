from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Dict, Any
import uuid
from datetime import datetime

from app.models.chat import ChatRequest, ChatResponse, ChatMessage, ConversationSession, ChatBody
from app.models.video import ProcessingStatus
from app.services.database import DatabaseService
from app.services.rag_service import RAGService

router = APIRouter()

def get_services(request: Request):
    """Dependency to get services from app state."""
    db_service = request.app.state.db_service
    rag_service = RAGService(db_service)
    return db_service, rag_service

@router.post("/chat/{video_id}", response_model=ChatResponse)
async def chat_with_video(
    video_id: str,
    request: ChatBody,
    services=Depends(get_services)
) -> ChatResponse:
    """Chat with video content using RAG."""
    db_service, rag_service = services
    
    try:
        # Validate video exists and is processed
        video_metadata = await db_service.get_video_metadata(video_id)
        if not video_metadata:
            raise HTTPException(status_code=404, detail="Video not found")
        
        if video_metadata.processing_status != ProcessingStatus.COMPLETED:
            status_messages = {
                ProcessingStatus.UPLOADING: "Video is still being uploaded",
                ProcessingStatus.PROCESSING: "Video is being processed",
                ProcessingStatus.TRANSCRIBING: "Video is being transcribed",
                ProcessingStatus.CHUNKING: "Transcript is being chunked",
                ProcessingStatus.EMBEDDING: "Embeddings are being created",
                ProcessingStatus.FAILED: "Video processing failed"
            }
            
            message = status_messages.get(
                video_metadata.processing_status,
                "Video is not ready for chat"
            )
            
            raise HTTPException(
                status_code=400, 
                detail=f"{message}. Please wait for processing to complete."
            )
        
        # Construct the full ChatRequest object
        full_chat_request = ChatRequest(
            video_id=video_id,
            question=request.question,
            conversation_history=request.conversation_history
        )

        # Generate response using RAG
        response = await rag_service.generate_response(full_chat_request)
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to process chat request")

@router.post("/chat/session")
async def create_chat_session(
    video_id: str,
    services=Depends(get_services)
) -> Dict[str, str]:
    """Create a new chat session for a video."""
    db_service, _ = services
    
    try:
        # Validate video exists
        video_metadata = await db_service.get_video_metadata(video_id)
        if not video_metadata:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Create session
        session_id = await db_service.create_conversation_session(video_id)
        
        return {
            "session_id": session_id,
            "video_id": video_id,
            "message": "Chat session created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating chat session: {e}")
        raise HTTPException(status_code=500, detail="Failed to create chat session")

@router.get("/chat/suggestions/{video_id}")
async def get_chat_suggestions(
    video_id: str,
    services=Depends(get_services)
) -> Dict[str, Any]:
    """Get suggested questions for a video."""
    db_service, _ = services
    
    try:
        # Validate video exists
        video_metadata = await db_service.get_video_metadata(video_id)
        if not video_metadata:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Generate suggestions based on video content
        suggestions = [
            "What are the main topics covered in this lecture?",
            "Can you summarize the key points?",
            "What examples were given to explain the concepts?",
            "What did the professor emphasize the most?",
            "Are there any important definitions I should know?",
            "What are the takeaways from this lecture?"
        ]
        
        # Add time-based suggestions if video is long
        if video_metadata.duration > 3600:  # More than 1 hour
            suggestions.extend([
                "What was discussed in the first hour?",
                "Can you summarize the second half of the lecture?",
                "What topics were covered around the middle of the lecture?"
            ])
        
        return {
            "video_id": video_id,
            "suggestions": suggestions,
            "video_title": video_metadata.title or video_metadata.filename,
            "duration": video_metadata.duration
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting chat suggestions: {e}")
        raise HTTPException(status_code=500, detail="Failed to get chat suggestions")

@router.get("/chat/search/{video_id}")
async def search_video_content(
    video_id: str,
    query: str,
    limit: int = 10,
    services=Depends(get_services)
) -> Dict[str, Any]:
    """Search for specific content in video transcript."""
    db_service, rag_service = services
    
    try:
        # Validate video exists
        video_metadata = await db_service.get_video_metadata(video_id)
        if not video_metadata:
            raise HTTPException(status_code=404, detail="Video not found")
        
        if video_metadata.processing_status != ProcessingStatus.COMPLETED:
            raise HTTPException(
                status_code=400, 
                detail="Video processing not complete"
            )
        
        # Search for relevant chunks
        relevant_chunks = await rag_service.retrieve_relevant_chunks(
            video_id, query, top_k=limit
        )
        
        return {
            "video_id": video_id,
            "query": query,
            "results": [
                {
                    "text": chunk.text,
                    "timestamp": chunk.formatted_timestamp,
                    "start_time": chunk.start_time,
                    "end_time": chunk.end_time,
                    "relevance_score": chunk.relevance_score
                }
                for chunk in relevant_chunks
            ],
            "total_results": len(relevant_chunks)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error searching video content: {e}")
        raise HTTPException(status_code=500, detail="Failed to search video content") 