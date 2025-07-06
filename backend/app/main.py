from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

# Import all routes
from app.routes import health, video, chat
from app.services.database import DatabaseService

load_dotenv()

# Create directories
os.makedirs("uploads", exist_ok=True)
os.makedirs("processed", exist_ok=True)
os.makedirs("vector_db", exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting Lecture RAG Application...")
    
    # Initialize database service
    db_service = DatabaseService()
    await db_service.initialize()
    app.state.db_service = db_service
    print("✅ Database service initialized")
    
    # Initialize RAG service with error handling
    try:
        from app.services.rag_service import RAGService
        rag_service = RAGService(db_service)
        await rag_service.initialize()
        app.state.rag_service = rag_service
        print("✅ RAG service initialized")
    except Exception as e:
        print(f"⚠️  RAG service initialization failed: {e}")
        print("⚠️  Chat functionality will be limited")
        app.state.rag_service = None
    
    print("✅ Application started successfully")
    yield
    
    # Shutdown
    print("🛑 Shutting down application...")
    await db_service.close()

app = FastAPI(
    title="Lecture RAG API",
    description="API for processing lecture videos and enabling RAG-based conversations",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files for serving uploaded videos
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/processed", StaticFiles(directory="processed"), name="processed")

# Include all routes
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(video.router, prefix="/api/v1", tags=["videos"])
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])

@app.get("/")
async def root():
    return {
        "message": "Lecture RAG API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
        "endpoints": {
            "videos": "/api/v1/videos",
            "upload": "/api/v1/videos/upload", 
            "chat": "/api/v1/chat/{video_id}"
        }
    }

if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    debug = os.getenv("DEBUG", "True").lower() == "true"
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info"
    ) 