from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks, Request
from typing import List, Dict, Any
import os
import uuid
import asyncio
from datetime import datetime
from pathlib import Path
import aiofiles

from app.models.video import (
    VideoMetadata, 
    ProcessingStatus, 
    VideoProcessingResponse, 
    VideoListResponse,
    VideoDetailResponse
)
from app.services.database import DatabaseService
from app.services.video_processor import VideoProcessor
from app.services.rag_service import RAGService

router = APIRouter()

# Maximum file size (2GB)
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 2000000000))

def get_services(request: Request):
    """Dependency to get services from app state."""
    db_service = request.app.state.db_service
    video_processor = VideoProcessor(db_service)
    rag_service = RAGService(db_service)
    return db_service, video_processor, rag_service

async def validate_video_file(file: UploadFile) -> bool:
    """Validate uploaded video file."""
    # Check file size
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE / (1024*1024*1024):.1f}GB"
        )
    
    # Check file extension
    allowed_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv'}
    file_ext = Path(file.filename).suffix.lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format. Allowed: {', '.join(allowed_extensions)}"
        )
    
    return True

async def process_video_pipeline(
    video_path: str, 
    video_metadata: VideoMetadata, 
    video_processor: VideoProcessor, 
    rag_service: RAGService
):
    """Background task for video processing pipeline."""
    try:
        # Process video (extract audio, transcribe, chunk)
        success = await video_processor.process_video(video_path, video_metadata)
        
        if success:
            # Create embeddings
            await rag_service.process_video_embeddings(video_metadata.id)
        
    except Exception as e:
        print(f"Error in video processing pipeline: {e}")
        await video_processor.db_service.update_processing_status(
            video_metadata.id, ProcessingStatus.FAILED, str(e)
        )

@router.post("/videos/upload", response_model=VideoProcessingResponse)
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    services=Depends(get_services)
) -> VideoProcessingResponse:
    """Upload a video file for processing."""
    db_service, video_processor, rag_service = services
    
    try:
        # Validate file
        await validate_video_file(file)
        
        # Generate unique video ID
        video_id = str(uuid.uuid4())
        
        # Save uploaded file
        upload_dir = Path("uploads")
        upload_dir.mkdir(exist_ok=True)
        
        file_extension = Path(file.filename).suffix
        video_filename = f"{video_id}{file_extension}"
        video_path = upload_dir / video_filename
        
        # Save file to disk
        async with aiofiles.open(video_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Get video duration
        duration = await video_processor.get_video_duration(str(video_path))
        
        # Create video metadata
        video_metadata = VideoMetadata(
            id=video_id,
            filename=file.filename,
            title=Path(file.filename).stem,
            duration=duration,
            file_size=len(content),
            upload_timestamp=datetime.now(),
            processing_status=ProcessingStatus.UPLOADING
        )
        
        # Save metadata to database
        await db_service.save_video_metadata(video_metadata)
        
        # Start background processing
        background_tasks.add_task(
            process_video_pipeline,
            str(video_path),
            video_metadata,
            video_processor,
            rag_service
        )
        
        return VideoProcessingResponse(
            video_id=video_id,
            status=ProcessingStatus.PROCESSING,
            message="Video uploaded successfully. Processing started."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error uploading video: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload video")

@router.get("/videos", response_model=VideoListResponse)
async def list_videos(services=Depends(get_services)) -> VideoListResponse:
    """Get list of all uploaded videos."""
    db_service, _, _ = services
    
    try:
        videos = await db_service.list_videos()
        return VideoListResponse(videos=videos, total=len(videos))
        
    except Exception as e:
        print(f"Error listing videos: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve videos")

@router.get("/videos/{video_id}", response_model=VideoDetailResponse)
async def get_video_details(
    video_id: str, 
    services=Depends(get_services)
) -> VideoDetailResponse:
    """Get detailed information about a specific video."""
    db_service, _, _ = services
    
    try:
        # Get video metadata
        metadata = await db_service.get_video_metadata(video_id)
        if not metadata:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Get transcript chunks
        chunks = await db_service.get_transcript_chunks(video_id)
        
        return VideoDetailResponse(metadata=metadata, chunks=chunks)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error retrieving video details: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve video details")

@router.get("/videos/{video_id}/status", response_model=VideoProcessingResponse)
async def get_video_status(
    video_id: str, 
    services=Depends(get_services)
) -> VideoProcessingResponse:
    """Get processing status of a video."""
    db_service, _, _ = services
    
    try:
        metadata = await db_service.get_video_metadata(video_id)
        if not metadata:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Calculate progress based on status
        progress_map = {
            ProcessingStatus.UPLOADING: 10.0,
            ProcessingStatus.PROCESSING: 20.0,
            ProcessingStatus.TRANSCRIBING: 40.0,
            ProcessingStatus.CHUNKING: 60.0,
            ProcessingStatus.EMBEDDING: 80.0,
            ProcessingStatus.COMPLETED: 100.0,
            ProcessingStatus.FAILED: 0.0
        }
        
        progress = progress_map.get(metadata.processing_status, 0.0)
        
        # Create status message
        status_messages = {
            ProcessingStatus.UPLOADING: "Uploading video...",
            ProcessingStatus.PROCESSING: "Extracting audio from video...",
            ProcessingStatus.TRANSCRIBING: "Transcribing audio with AI...",
            ProcessingStatus.CHUNKING: "Creating intelligent chunks...",
            ProcessingStatus.EMBEDDING: "Generating vector embeddings...",
            ProcessingStatus.COMPLETED: "Processing completed successfully!",
            ProcessingStatus.FAILED: f"Processing failed: {metadata.processing_error or 'Unknown error'}"
        }
        
        message = status_messages.get(
            metadata.processing_status, 
            "Unknown processing status"
        )
        
        return VideoProcessingResponse(
            video_id=video_id,
            status=metadata.processing_status,
            message=message,
            progress=progress
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error retrieving video status: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve video status")

@router.delete("/videos/{video_id}")
async def delete_video(
    video_id: str, 
    services=Depends(get_services)
) -> Dict[str, str]:
    """Delete a video and all associated data."""
    db_service, _, _ = services
    
    try:
        # Check if video exists
        metadata = await db_service.get_video_metadata(video_id)
        if not metadata:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # TODO: Implement proper deletion
        # - Remove video file
        # - Remove audio file
        # - Remove transcript file
        # - Remove from vector database
        # - Remove from SQLite database
        
        return {"message": f"Video {video_id} deletion queued"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting video: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete video") 