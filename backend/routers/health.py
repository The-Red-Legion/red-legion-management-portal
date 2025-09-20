"""Health check and monitoring endpoints."""

from fastapi import APIRouter

router = APIRouter()

@router.get("/ping")
@router.get("/mgmt/api/ping")
async def ping():
    """Simple ping endpoint for health checks."""
    return {"status": "ok", "message": "Red Legion Management Portal API is running"}

@router.get("/health")
@router.get("/mgmt/api/health")
async def health():
    """Detailed health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "service": "Red Legion Management Portal",
        "timestamp": "2024-01-01T00:00:00Z"
    }