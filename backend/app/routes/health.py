from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import os
import time
from datetime import datetime

router = APIRouter()

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "service": "lecture-rag-api"
    }

@router.get("/health/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """Detailed health check with component status."""
    try:
        # Check if required environment variables are set
        gemini_key_set = bool(os.getenv("GEMINI_API_KEY"))
        
        # Check if directories exist
        upload_dir_exists = os.path.exists("uploads")
        processed_dir_exists = os.path.exists("processed")
        vector_db_dir_exists = os.path.exists("vector_db")
        
        components = {
            "api": "healthy",
            "gemini_api_key": "configured" if gemini_key_set else "missing",
            "upload_directory": "ready" if upload_dir_exists else "missing",
            "processed_directory": "ready" if processed_dir_exists else "missing",
            "vector_database": "ready" if vector_db_dir_exists else "missing"
        }
        
        # Overall status
        all_healthy = all(
            status in ["healthy", "ready", "configured"] 
            for status in components.values()
        )
        
        return {
            "status": "healthy" if all_healthy else "degraded",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "components": components
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        } 