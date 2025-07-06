import os
import uuid
import asyncio
import time
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import google.generativeai as genai
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings
import numpy as np
import re

from app.models.video import TranscriptChunk, ProcessingStatus
from app.models.chat import ChatRequest, ChatResponse, RelevantChunk, ChatMessage
from app.services.database import DatabaseService

class RAGService:
    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service
        self.embedding_model = None
        self.chroma_client = None
        self.gemini_model = None
        
        # Initialize Gemini
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            self.gemini_model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # Initialize ChromaDB
        self._initialize_chroma()
    
    def _initialize_chroma(self):
        """Initialize ChromaDB client and collection."""
        try:
            self.chroma_client = chromadb.PersistentClient(path="./vector_db")
            print("ChromaDB initialized successfully")
        except Exception as e:
            print(f"Error initializing ChromaDB: {e}")
    
    async def initialize(self):
        """Initialize the RAG service with required models and services."""
        try:
            print("Initializing RAG service...")
            
            # Initialize embedding model (lazy loading)
            # This will be loaded when needed to avoid startup delays
            
            # Verify ChromaDB is working
            if self.chroma_client is None:
                self._initialize_chroma()
            
            # Test Gemini connection if API key is available
            if self.gemini_model:
                print("Gemini model configured successfully")
            else:
                print("Warning: Gemini API key not found - chat functionality will be limited")
                
            print("RAG service initialized successfully")
            
        except Exception as e:
            print(f"Error initializing RAG service: {e}")
            raise
    
    def _load_embedding_model(self):
        """Load sentence transformer model lazily."""
        if self.embedding_model is None:
            print("Loading embedding model...")
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            print("Embedding model loaded successfully")
    
    def _format_timestamp(self, seconds: float) -> str:
        """Format seconds to MM:SS or HH:MM:SS format."""
        hours, remainder = divmod(int(seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"
    
    async def create_embeddings(self, chunks: List[TranscriptChunk]) -> bool:
        """Create vector embeddings for transcript chunks."""
        try:
            if not chunks:
                return True
            
            print(f"Creating embeddings for {len(chunks)} chunks...")
            self._load_embedding_model()
            
            video_id = chunks[0].video_id
            
            # Get or create collection for this video
            collection_name = f"video_{video_id.replace('-', '_')}"
            try:
                collection = self.chroma_client.get_collection(collection_name)
                # Clear existing embeddings for this video
                collection.delete()
            except:
                pass
            
            collection = self.chroma_client.create_collection(
                name=collection_name,
                metadata={"video_id": video_id}
            )
            
            # Prepare data for embedding
            texts = [chunk.text for chunk in chunks]
            ids = [chunk.id for chunk in chunks]
            
            # Create embeddings in batches
            batch_size = 50
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                batch_ids = ids[i:i + batch_size]
                batch_chunks = chunks[i:i + batch_size]
                
                # Generate embeddings
                loop = asyncio.get_event_loop()
                embeddings = await loop.run_in_executor(
                    None, 
                    self.embedding_model.encode, 
                    batch_texts
                )
                
                # Prepare metadata
                metadatas = [
                    {
                        "video_id": chunk.video_id,
                        "start_time": chunk.start_time,
                        "end_time": chunk.end_time,
                        "chunk_index": chunk.chunk_index,
                        "word_count": chunk.word_count,
                        "formatted_timestamp": self._format_timestamp(chunk.start_time)
                    }
                    for chunk in batch_chunks
                ]
                
                # Add to collection
                collection.add(
                    embeddings=embeddings.tolist(),
                    documents=batch_texts,
                    metadatas=metadatas,
                    ids=batch_ids
                )
                
                print(f"Processed batch {i//batch_size + 1}/{(len(texts) + batch_size - 1)//batch_size}")
            
            print(f"Successfully created embeddings for video {video_id}")
            return True
            
        except Exception as e:
            print(f"Error creating embeddings: {e}")
            return False
    
    async def retrieve_relevant_chunks(
        self, 
        video_id: str, 
        query: str, 
        top_k: int = 5
    ) -> List[RelevantChunk]:
        """Retrieve relevant chunks for a given query."""
        try:
            self._load_embedding_model()
            
            # Get collection for this video
            collection_name = f"video_{video_id.replace('-', '_')}"
            collection = self.chroma_client.get_collection(collection_name)
            
            # Create query embedding
            loop = asyncio.get_event_loop()
            query_embedding = await loop.run_in_executor(
                None, 
                self.embedding_model.encode, 
                [query]
            )
            
            # Search for similar chunks
            results = collection.query(
                query_embeddings=query_embedding.tolist(),
                n_results=top_k,
                include=["documents", "metadatas", "distances"]
            )
            
            # Convert to RelevantChunk objects
            relevant_chunks = []
            for i, (doc, metadata, distance) in enumerate(zip(
                results['documents'][0],
                results['metadatas'][0], 
                results['distances'][0]
            )):
                # Convert distance to relevance score (cosine similarity)
                relevance_score = max(0, 1 - distance)
                
                relevant_chunk = RelevantChunk(
                    chunk_id=results['ids'][0][i],
                    text=doc,
                    start_time=metadata['start_time'],
                    end_time=metadata['end_time'],
                    relevance_score=relevance_score,
                    formatted_timestamp=metadata['formatted_timestamp']
                )
                relevant_chunks.append(relevant_chunk)
            
            return relevant_chunks
            
        except Exception as e:
            print(f"Error retrieving relevant chunks: {e}")
            return []
    
    def _build_context(self, relevant_chunks: List[RelevantChunk]) -> str:
        """Build context string from relevant chunks."""
        if not relevant_chunks:
            return ""
        
        context_parts = []
        for chunk in relevant_chunks:
            timestamp = chunk.formatted_timestamp
            text = chunk.text
            context_parts.append(f"[{timestamp}] {text}")
        
        return "\n\n".join(context_parts)
    
    def _build_conversation_context(self, conversation_history: List[ChatMessage]) -> str:
        """Build conversation context from chat history."""
        if not conversation_history:
            return ""
        
        # Take last 5 messages for context
        recent_messages = conversation_history[-5:]
        context_parts = []
        
        for msg in recent_messages:
            role = "Human" if msg.role == "user" else "Assistant"
            context_parts.append(f"{role}: {msg.content}")
        
        return "\n".join(context_parts)
    
    async def generate_response(self, request: ChatRequest) -> ChatResponse:
        """Generate AI response using retrieved context and Gemini."""
        start_time = time.time()
        
        try:
            # Retrieve relevant chunks
            relevant_chunks = await self.retrieve_relevant_chunks(
                request.video_id, 
                request.question, 
                top_k=5
            )
            
            if not relevant_chunks:
                return ChatResponse(
                    answer="I couldn't find relevant information in the lecture to answer your question. Please try rephrasing or asking about a different topic.",
                    relevant_chunks=[],
                    video_id=request.video_id,
                    confidence_score=0.0,
                    processing_time=time.time() - start_time
                )
            
            # Build context
            lecture_context = self._build_context(relevant_chunks)
            conversation_context = self._build_conversation_context(request.conversation_history)
            
            # Create prompt
            prompt = f"""You are an AI teaching assistant helping students understand lecture content. Based on the provided lecture transcript excerpts, answer the student's question accurately and helpfully.

Lecture Context:
{lecture_context}

{f"Previous Conversation:{conversation_context}" if conversation_context else ""}

Student Question: {request.question}

Instructions:
1. Answer based ONLY on the information provided in the lecture context
2. If the question cannot be answered from the context, say so politely
3. Include relevant timestamps in your response when referring to specific parts
4. Be educational and explain concepts clearly
5. If you reference specific quotes or examples, mention the timestamp
6. Keep responses focused and concise but thorough

Answer:"""

            # Generate response using Gemini
            if not self.gemini_model:
                raise Exception("Gemini model not initialized")
            
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.gemini_model.generate_content(prompt)
            )
            
            answer = response.text.strip() if response.text else "I'm unable to generate a response at the moment."
            
            # Calculate confidence score based on relevance of chunks
            avg_relevance = sum(chunk.relevance_score for chunk in relevant_chunks) / len(relevant_chunks)
            confidence_score = min(0.95, avg_relevance)
            
            return ChatResponse(
                answer=answer,
                relevant_chunks=relevant_chunks,
                video_id=request.video_id,
                confidence_score=confidence_score,
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            print(f"Error generating response: {e}")
            return ChatResponse(
                answer="I'm experiencing technical difficulties. Please try again later.",
                relevant_chunks=relevant_chunks if 'relevant_chunks' in locals() else [],
                video_id=request.video_id,
                confidence_score=0.0,
                processing_time=time.time() - start_time
            )
    
    async def process_video_embeddings(self, video_id: str) -> bool:
        """Process embeddings for a video after transcript chunks are created."""
        try:
            # Update status
            await self.db_service.update_processing_status(video_id, ProcessingStatus.EMBEDDING)
            
            # Get transcript chunks
            chunks = await self.db_service.get_transcript_chunks(video_id)
            if not chunks:
                await self.db_service.update_processing_status(
                    video_id, ProcessingStatus.FAILED, "No transcript chunks found"
                )
                return False
            
            # Create embeddings
            if not await self.create_embeddings(chunks):
                await self.db_service.update_processing_status(
                    video_id, ProcessingStatus.FAILED, "Embedding creation failed"
                )
                return False
            
            # Mark as completed
            await self.db_service.update_processing_status(video_id, ProcessingStatus.COMPLETED)
            print(f"Video processing fully completed for {video_id}")
            return True
            
        except Exception as e:
            print(f"Error processing video embeddings: {e}")
            await self.db_service.update_processing_status(
                video_id, ProcessingStatus.FAILED, str(e)
            )
            return False 