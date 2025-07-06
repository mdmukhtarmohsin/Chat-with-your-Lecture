from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class ProcessingStatus(str, Enum):
    UPLOADING = "uploading"
    PROCESSING = "processing"
    TRANSCRIBING = "transcribing"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    COMPLETED = "completed"
    FAILED = "failed"

class VideoUpload(BaseModel):
    filename: str = Field(..., description="Original filename of the uploaded video")
    file_size: int = Field(..., description="Size of the uploaded file in bytes")
    content_type: str = Field(..., description="MIME type of the uploaded file")

class TranscriptChunk(BaseModel):
    id: str = Field(..., description="Unique identifier for the chunk")
    video_id: str = Field(..., description="ID of the parent video")
    text: str = Field(..., description="Text content of the chunk")
    start_time: float = Field(..., description="Start timestamp in seconds")
    end_time: float = Field(..., description="End timestamp in seconds")
    chunk_index: int = Field(..., description="Index of the chunk in the video")
    word_count: int = Field(..., description="Number of words in the chunk")

class VideoMetadata(BaseModel):
    id: str = Field(..., description="Unique video identifier")
    filename: str = Field(..., description="Original filename")
    title: Optional[str] = Field(None, description="Video title")
    duration: float = Field(..., description="Video duration in seconds")
    file_size: int = Field(..., description="File size in bytes")
    upload_timestamp: datetime = Field(..., description="Upload timestamp")
    processing_status: ProcessingStatus = Field(..., description="Current processing status")
    audio_path: Optional[str] = Field(None, description="Path to extracted audio file")
    transcript_path: Optional[str] = Field(None, description="Path to transcript file")
    total_chunks: Optional[int] = Field(None, description="Total number of chunks")
    processing_error: Optional[str] = Field(None, description="Error message if processing failed")

class VideoSummary(BaseModel):
    video_id: str
    title: str
    duration: float
    total_chunks: int
    processing_status: ProcessingStatus
    upload_timestamp: datetime
    
class VideoProcessingResponse(BaseModel):
    video_id: str
    status: ProcessingStatus
    message: str
    progress: Optional[float] = Field(None, description="Processing progress percentage")

class VideoListResponse(BaseModel):
    videos: List[VideoSummary]
    total: int
    
class VideoDetailResponse(BaseModel):
    metadata: VideoMetadata
    chunks: List[TranscriptChunk] 