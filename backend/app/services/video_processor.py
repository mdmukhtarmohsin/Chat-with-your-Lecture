import os
import uuid
import asyncio
import ffmpeg
import whisper
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import re
from pathlib import Path

from app.models.video import VideoMetadata, TranscriptChunk, ProcessingStatus
from app.services.database import DatabaseService

class VideoProcessor:
    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service
        self.whisper_model = None
        self.upload_dir = Path("uploads")
        self.processed_dir = Path("processed")
        
        # Ensure directories exist
        self.upload_dir.mkdir(exist_ok=True)
        self.processed_dir.mkdir(exist_ok=True)
    
    def _load_whisper_model(self):
        """Load Whisper model lazily."""
        if self.whisper_model is None:
            print("Loading Whisper model...")
            self.whisper_model = whisper.load_model("base")
            print("Whisper model loaded successfully")
    
    async def get_video_duration(self, video_path: str) -> float:
        """Get video duration in seconds using ffmpeg."""
        try:
            probe = ffmpeg.probe(video_path)
            duration = float(probe['streams'][0]['duration'])
            return duration
        except Exception as e:
            print(f"Error getting video duration: {e}")
            return 0.0
    
    async def extract_audio(self, video_path: str, audio_path: str) -> bool:
        """Extract audio from video file."""
        try:
            print(f"Extracting audio from {video_path}")
            
            # Use ffmpeg to extract audio
            (
                ffmpeg
                .input(video_path)
                .output(audio_path, acodec='pcm_s16le', ac=1, ar='16000')
                .overwrite_output()
                .run(quiet=True)
            )
            
            print(f"Audio extracted to {audio_path}")
            return True
            
        except Exception as e:
            print(f"Error extracting audio: {e}")
            return False
    
    async def transcribe_audio(self, audio_path: str) -> Optional[Dict[str, Any]]:
        """Transcribe audio using Whisper with timestamp information."""
        try:
            print(f"Transcribing audio: {audio_path}")
            self._load_whisper_model()
            
            # Run transcription in a thread to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                lambda: self.whisper_model.transcribe(
                    audio_path, 
                    word_timestamps=True,
                    verbose=False
                )
            )
            
            print(f"Transcription completed. Language: {result.get('language', 'unknown')}")
            return result
            
        except Exception as e:
            print(f"Error transcribing audio: {e}")
            return None
    
    def _format_timestamp(self, seconds: float) -> str:
        """Format seconds to HH:MM:SS format."""
        td = timedelta(seconds=seconds)
        hours, remainder = divmod(td.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
    
    def _chunk_transcript_by_time(self, segments: List[Dict], chunk_duration: int = 60) -> List[Dict]:
        """Chunk transcript segments by time duration (in seconds)."""
        chunks = []
        current_chunk = {
            'text': '',
            'start': None,
            'end': None,
            'words': []
        }
        
        for segment in segments:
            segment_start = segment['start']
            segment_end = segment['end']
            segment_text = segment['text'].strip()
            
            # Initialize chunk if empty
            if current_chunk['start'] is None:
                current_chunk['start'] = segment_start
            
            # Check if adding this segment would exceed chunk duration
            if (segment_end - current_chunk['start']) > chunk_duration and current_chunk['text']:
                # Finalize current chunk
                current_chunk['end'] = current_chunk.get('end', segment_start)
                chunks.append(current_chunk.copy())
                
                # Start new chunk
                current_chunk = {
                    'text': segment_text,
                    'start': segment_start,
                    'end': segment_end,
                    'words': segment.get('words', [])
                }
            else:
                # Add to current chunk
                current_chunk['text'] += ' ' + segment_text if current_chunk['text'] else segment_text
                current_chunk['end'] = segment_end
                if 'words' in segment:
                    current_chunk['words'].extend(segment['words'])
        
        # Add final chunk
        if current_chunk['text']:
            chunks.append(current_chunk)
        
        return chunks
    
    def _chunk_transcript_by_content(self, segments: List[Dict], max_words: int = 200) -> List[Dict]:
        """Chunk transcript by content boundaries (sentences, topics)."""
        chunks = []
        current_chunk = {
            'text': '',
            'start': None,
            'end': None,
            'word_count': 0
        }
        
        for segment in segments:
            segment_text = segment['text'].strip()
            segment_words = len(segment_text.split())
            
            # Initialize chunk if empty
            if current_chunk['start'] is None:
                current_chunk['start'] = segment['start']
            
            # Check if adding this segment would exceed word limit
            if (current_chunk['word_count'] + segment_words) > max_words and current_chunk['text']:
                # Look for sentence boundary
                sentences = re.split(r'[.!?]+', current_chunk['text'])
                if len(sentences) > 1:
                    # Keep complete sentences in current chunk
                    complete_text = '. '.join(sentences[:-1]) + '.'
                    current_chunk['text'] = complete_text.strip()
                
                chunks.append(current_chunk.copy())
                
                # Start new chunk with remaining text or current segment
                remaining_text = sentences[-1].strip() if len(sentences) > 1 else ''
                current_chunk = {
                    'text': remaining_text + ' ' + segment_text if remaining_text else segment_text,
                    'start': segment['start'],
                    'end': segment['end'],
                    'word_count': len((remaining_text + ' ' + segment_text).split()) if remaining_text else segment_words
                }
            else:
                # Add to current chunk
                current_chunk['text'] += ' ' + segment_text if current_chunk['text'] else segment_text
                current_chunk['end'] = segment['end']
                current_chunk['word_count'] += segment_words
        
        # Add final chunk
        if current_chunk['text']:
            chunks.append(current_chunk)
        
        return chunks
    
    async def create_transcript_chunks(
        self, 
        video_id: str, 
        transcription_result: Dict[str, Any],
        strategy: str = "hybrid"
    ) -> List[TranscriptChunk]:
        """Create transcript chunks with timestamps."""
        try:
            segments = transcription_result.get('segments', [])
            if not segments:
                return []
            
            # Choose chunking strategy
            if strategy == "time":
                raw_chunks = self._chunk_transcript_by_time(segments, chunk_duration=90)
            elif strategy == "content":
                raw_chunks = self._chunk_transcript_by_content(segments, max_words=150)
            else:  # hybrid
                # First chunk by time, then refine by content
                time_chunks = self._chunk_transcript_by_time(segments, chunk_duration=120)
                raw_chunks = []
                for chunk in time_chunks:
                    # Further split large chunks by content
                    if len(chunk['text'].split()) > 200:
                        # Create mini-segments for content-based splitting
                        mini_segments = [{'text': chunk['text'], 'start': chunk['start'], 'end': chunk['end']}]
                        content_chunks = self._chunk_transcript_by_content(mini_segments, max_words=150)
                        raw_chunks.extend(content_chunks)
                    else:
                        raw_chunks.append(chunk)
            
            # Convert to TranscriptChunk objects
            chunks = []
            for i, chunk in enumerate(raw_chunks):
                chunk_id = str(uuid.uuid4())
                
                # Clean up text
                text = re.sub(r'\s+', ' ', chunk['text']).strip()
                if not text:
                    continue
                
                transcript_chunk = TranscriptChunk(
                    id=chunk_id,
                    video_id=video_id,
                    text=text,
                    start_time=chunk['start'],
                    end_time=chunk['end'],
                    chunk_index=i,
                    word_count=len(text.split())
                )
                chunks.append(transcript_chunk)
            
            print(f"Created {len(chunks)} transcript chunks")
            return chunks
            
        except Exception as e:
            print(f"Error creating transcript chunks: {e}")
            return []
    
    async def save_transcript_to_file(self, video_id: str, transcription_result: Dict[str, Any]) -> str:
        """Save full transcript to a text file."""
        try:
            transcript_path = self.processed_dir / f"{video_id}_transcript.txt"
            
            with open(transcript_path, 'w', encoding='utf-8') as f:
                f.write(f"Transcript for Video ID: {video_id}\n")
                f.write(f"Generated: {datetime.now().isoformat()}\n")
                f.write("=" * 50 + "\n\n")
                
                for segment in transcription_result.get('segments', []):
                    start_time = self._format_timestamp(segment['start'])
                    end_time = self._format_timestamp(segment['end'])
                    text = segment['text'].strip()
                    
                    f.write(f"[{start_time} - {end_time}]\n")
                    f.write(f"{text}\n\n")
            
            return str(transcript_path)
            
        except Exception as e:
            print(f"Error saving transcript to file: {e}")
            return ""
    
    async def process_video(self, video_path: str, video_metadata: VideoMetadata) -> bool:
        """Main video processing pipeline."""
        try:
            video_id = video_metadata.id
            
            # Update status: Processing
            await self.db_service.update_processing_status(video_id, ProcessingStatus.PROCESSING)
            
            # Extract audio
            audio_path = self.processed_dir / f"{video_id}_audio.wav"
            if not await self.extract_audio(video_path, str(audio_path)):
                await self.db_service.update_processing_status(
                    video_id, ProcessingStatus.FAILED, "Audio extraction failed"
                )
                return False
            
            # Update metadata with audio path
            video_metadata.audio_path = str(audio_path)
            await self.db_service.save_video_metadata(video_metadata)
            
            # Update status: Transcribing
            await self.db_service.update_processing_status(video_id, ProcessingStatus.TRANSCRIBING)
            
            # Transcribe audio
            transcription_result = await self.transcribe_audio(str(audio_path))
            if not transcription_result:
                await self.db_service.update_processing_status(
                    video_id, ProcessingStatus.FAILED, "Transcription failed"
                )
                return False
            
            # Save full transcript
            transcript_path = await self.save_transcript_to_file(video_id, transcription_result)
            video_metadata.transcript_path = transcript_path
            
            # Update status: Chunking
            await self.db_service.update_processing_status(video_id, ProcessingStatus.CHUNKING)
            
            # Create chunks
            chunks = await self.create_transcript_chunks(video_id, transcription_result)
            if not chunks:
                await self.db_service.update_processing_status(
                    video_id, ProcessingStatus.FAILED, "Chunking failed"
                )
                return False
            
            # Save chunks to database
            if not await self.db_service.save_transcript_chunks(chunks):
                await self.db_service.update_processing_status(
                    video_id, ProcessingStatus.FAILED, "Failed to save chunks"
                )
                return False
            
            # Update metadata with chunk count
            video_metadata.total_chunks = len(chunks)
            await self.db_service.save_video_metadata(video_metadata)
            
            # Update status: Embedding (will be handled by RAG service)
            await self.db_service.update_processing_status(video_id, ProcessingStatus.EMBEDDING)
            
            print(f"Video processing completed successfully for {video_id}")
            return True
            
        except Exception as e:
            print(f"Error in video processing pipeline: {e}")
            await self.db_service.update_processing_status(
                video_id, ProcessingStatus.FAILED, str(e)
            )
            return False 