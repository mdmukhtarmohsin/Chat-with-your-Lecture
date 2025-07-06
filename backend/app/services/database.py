import sqlite3
import json
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager
import aiosqlite

from app.models.video import VideoMetadata, TranscriptChunk, ProcessingStatus, VideoSummary
from app.models.chat import ConversationSession, ChatMessage

class DatabaseService:
    def __init__(self, db_path: str = "lecture_rag.db"):
        self.db_path = db_path
    
    async def initialize(self):
        """Initialize the database with required tables."""
        async with aiosqlite.connect(self.db_path) as db:
            await self._create_tables(db)
            await db.commit()
    
    async def _create_tables(self, db: aiosqlite.Connection):
        """Create all required database tables."""
        
        # Videos table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                title TEXT,
                duration REAL NOT NULL,
                file_size INTEGER NOT NULL,
                upload_timestamp TEXT NOT NULL,
                processing_status TEXT NOT NULL,
                audio_path TEXT,
                transcript_path TEXT,
                total_chunks INTEGER,
                processing_error TEXT
            )
        """)
        
        # Transcript chunks table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS transcript_chunks (
                id TEXT PRIMARY KEY,
                video_id TEXT NOT NULL,
                text TEXT NOT NULL,
                start_time REAL NOT NULL,
                end_time REAL NOT NULL,
                chunk_index INTEGER NOT NULL,
                word_count INTEGER NOT NULL,
                FOREIGN KEY (video_id) REFERENCES videos (id) ON DELETE CASCADE
            )
        """)
        
        # Conversation sessions table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS conversation_sessions (
                session_id TEXT PRIMARY KEY,
                video_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_activity TEXT NOT NULL,
                FOREIGN KEY (video_id) REFERENCES videos (id) ON DELETE CASCADE
            )
        """)
        
        # Chat messages table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES conversation_sessions (session_id) ON DELETE CASCADE
            )
        """)
        
        # Create indexes for better performance
        await db.execute("CREATE INDEX IF NOT EXISTS idx_chunks_video_id ON transcript_chunks (video_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_chunks_time ON transcript_chunks (start_time, end_time)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON chat_messages (session_id)")
    
    async def save_video_metadata(self, metadata: VideoMetadata) -> bool:
        """Save video metadata to database."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO videos 
                    (id, filename, title, duration, file_size, upload_timestamp, 
                     processing_status, audio_path, transcript_path, total_chunks, processing_error)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    metadata.id, metadata.filename, metadata.title, metadata.duration,
                    metadata.file_size, metadata.upload_timestamp.isoformat(),
                    metadata.processing_status.value, metadata.audio_path,
                    metadata.transcript_path, metadata.total_chunks, metadata.processing_error
                ))
                await db.commit()
                return True
        except Exception as e:
            print(f"Error saving video metadata: {e}")
            return False
    
    async def get_video_metadata(self, video_id: str) -> Optional[VideoMetadata]:
        """Retrieve video metadata by ID."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("SELECT * FROM videos WHERE id = ?", (video_id,)) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        return VideoMetadata(
                            id=row['id'],
                            filename=row['filename'],
                            title=row['title'],
                            duration=row['duration'],
                            file_size=row['file_size'],
                            upload_timestamp=datetime.fromisoformat(row['upload_timestamp']),
                            processing_status=ProcessingStatus(row['processing_status']),
                            audio_path=row['audio_path'],
                            transcript_path=row['transcript_path'],
                            total_chunks=row['total_chunks'],
                            processing_error=row['processing_error']
                        )
                    return None
        except Exception as e:
            print(f"Error retrieving video metadata: {e}")
            return None
    
    async def save_transcript_chunks(self, chunks: List[TranscriptChunk]) -> bool:
        """Save transcript chunks to database."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                chunk_data = [
                    (chunk.id, chunk.video_id, chunk.text, chunk.start_time,
                     chunk.end_time, chunk.chunk_index, chunk.word_count)
                    for chunk in chunks
                ]
                await db.executemany("""
                    INSERT OR REPLACE INTO transcript_chunks 
                    (id, video_id, text, start_time, end_time, chunk_index, word_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, chunk_data)
                await db.commit()
                return True
        except Exception as e:
            print(f"Error saving transcript chunks: {e}")
            return False
    
    async def get_transcript_chunks(self, video_id: str) -> List[TranscriptChunk]:
        """Retrieve all transcript chunks for a video."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("""
                    SELECT * FROM transcript_chunks 
                    WHERE video_id = ? 
                    ORDER BY chunk_index
                """, (video_id,)) as cursor:
                    rows = await cursor.fetchall()
                    return [
                        TranscriptChunk(
                            id=row['id'],
                            video_id=row['video_id'],
                            text=row['text'],
                            start_time=row['start_time'],
                            end_time=row['end_time'],
                            chunk_index=row['chunk_index'],
                            word_count=row['word_count']
                        )
                        for row in rows
                    ]
        except Exception as e:
            print(f"Error retrieving transcript chunks: {e}")
            return []
    
    async def list_videos(self) -> List[VideoSummary]:
        """List all videos with summary information."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("""
                    SELECT id, filename, title, duration, total_chunks, 
                           processing_status, upload_timestamp
                    FROM videos 
                    ORDER BY upload_timestamp DESC
                """) as cursor:
                    rows = await cursor.fetchall()
                    return [
                        VideoSummary(
                            video_id=row['id'],
                            title=row['title'] or row['filename'],
                            duration=row['duration'],
                            total_chunks=row['total_chunks'] or 0,
                            processing_status=ProcessingStatus(row['processing_status']),
                            upload_timestamp=datetime.fromisoformat(row['upload_timestamp'])
                        )
                        for row in rows
                    ]
        except Exception as e:
            print(f"Error listing videos: {e}")
            return []
    
    async def update_processing_status(self, video_id: str, status: ProcessingStatus, error: Optional[str] = None) -> bool:
        """Update the processing status of a video."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE videos 
                    SET processing_status = ?, processing_error = ?
                    WHERE id = ?
                """, (status.value, error, video_id))
                await db.commit()
                return True
        except Exception as e:
            print(f"Error updating processing status: {e}")
            return False
    
    async def create_conversation_session(self, video_id: str) -> str:
        """Create a new conversation session."""
        session_id = str(uuid.uuid4())
        try:
            async with aiosqlite.connect(self.db_path) as db:
                now = datetime.now().isoformat()
                await db.execute("""
                    INSERT INTO conversation_sessions 
                    (session_id, video_id, created_at, last_activity)
                    VALUES (?, ?, ?, ?)
                """, (session_id, video_id, now, now))
                await db.commit()
                return session_id
        except Exception as e:
            print(f"Error creating conversation session: {e}")
            return session_id
    
    async def save_chat_message(self, session_id: str, message: ChatMessage) -> bool:
        """Save a chat message to the database."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                message_id = str(uuid.uuid4())
                await db.execute("""
                    INSERT INTO chat_messages 
                    (id, session_id, role, content, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """, (message_id, session_id, message.role, message.content, message.timestamp.isoformat()))
                
                # Update last activity
                await db.execute("""
                    UPDATE conversation_sessions 
                    SET last_activity = ? 
                    WHERE session_id = ?
                """, (datetime.now().isoformat(), session_id))
                
                await db.commit()
                return True
        except Exception as e:
            print(f"Error saving chat message: {e}")
            return False

    async def close(self):
        """Close database connections and clean up resources."""
        # SQLite connections are automatically closed in aiosqlite context managers
        # This method is here for interface consistency and future extensibility
        pass 