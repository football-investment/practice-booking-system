from typing import Any, Dict
from fastapi import APIRouter, Request
from datetime import datetime
import platform
import sys

router = APIRouter()


@router.get("/health", response_model=Dict[str, Any])
@router.head("/health")
def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for debugging
    Supports both GET and HEAD methods
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "message": "Practice Booking System API is running"
    }


@router.get("/environment", response_model=Dict[str, Any])
def get_environment_info() -> Dict[str, Any]:
    """
    Get server environment information for debugging
    """
    return {
        "python_version": sys.version,
        "platform": platform.platform(),
        "architecture": platform.architecture(),
        "processor": platform.processor(),
        "timestamp": datetime.now().isoformat(),
        "server_info": {
            "os": platform.system(),
            "release": platform.release(),
            "machine": platform.machine()
        }
    }


@router.post("/log-error")
def log_frontend_error(error_data: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """
    Log frontend errors for debugging
    """
    client_ip = request.client.host
    user_agent = request.headers.get("user-agent", "Unknown")
    
    # In a real application, you would log this to a file or database
    print(f"🚨 Frontend Error from {client_ip}:")
    print(f"User Agent: {user_agent}")
    print(f"Error Data: {error_data}")
    
    return {
        "status": "logged",
        "timestamp": datetime.now().isoformat(),
        "client_ip": client_ip
    }