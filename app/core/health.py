import time
import os
import platform
from datetime import datetime, timezone
from typing import Dict, Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from ..database import SessionLocal
from ..config import settings


class HealthChecker:
    """Comprehensive health monitoring for production deployment."""
    
    @staticmethod
    async def get_database_health() -> Dict[str, Any]:
        """Check database connectivity and performance."""
        db_health = {
            "status": "unknown",
            "response_time_ms": 0,
            "error": None,
            "details": {}
        }
        
        start_time = time.time()
        
        try:
            db = SessionLocal()
            
            # Test basic connectivity
            result = db.execute(text("SELECT 1")).scalar()
            
            # Test table access
            user_count = db.execute(text("SELECT COUNT(*) FROM users")).scalar()
            session_count = db.execute(text("SELECT COUNT(*) FROM sessions")).scalar()
            booking_count = db.execute(text("SELECT COUNT(*) FROM bookings")).scalar()
            
            response_time = round((time.time() - start_time) * 1000, 2)
            
            db_health.update({
                "status": "healthy" if result == 1 else "degraded",
                "response_time_ms": response_time,
                "details": {
                    "users_count": user_count,
                    "sessions_count": session_count,
                    "bookings_count": booking_count,
                    "connection_test": result == 1
                }
            })
            
            # Performance warning
            if response_time > 1000:  # 1 second threshold
                db_health["status"] = "degraded"
                db_health["warning"] = "Database response time is slow"
                
        except SQLAlchemyError as e:
            db_health.update({
                "status": "unhealthy",
                "response_time_ms": round((time.time() - start_time) * 1000, 2),
                "error": str(e),
                "details": {"connection_failed": True}
            })
        finally:
            try:
                db.close()
            except:
                pass
        
        return db_health
    
    @staticmethod
    def get_system_health() -> Dict[str, Any]:
        """Check system resource health."""
        try:
            # Basic system info without psutil
            load_avg = None
            try:
                load_avg = os.getloadavg()  # Unix systems only
            except (AttributeError, OSError):
                pass
            
            # Get basic disk info
            disk_info = None
            try:
                statvfs = os.statvfs('/')
                total_space = statvfs.f_frsize * statvfs.f_blocks
                free_space = statvfs.f_frsize * statvfs.f_available
                used_percent = (total_space - free_space) / total_space * 100
                
                disk_info = {
                    "total_gb": round(total_space / (1024**3), 2),
                    "free_gb": round(free_space / (1024**3), 2),
                    "percent_used": round(used_percent, 1)
                }
            except (AttributeError, OSError):
                pass
            
            # Determine status based on available metrics
            status = "healthy"
            warnings = []
            
            if load_avg and len(load_avg) > 0 and load_avg[0] > 4.0:
                status = "degraded"
                warnings.append(f"High system load: {load_avg[0]}")
            
            if disk_info and disk_info["percent_used"] > 85:
                status = "degraded"
                warnings.append(f"High disk usage: {disk_info['percent_used']}%")
            
            return {
                "status": status,
                "platform": {
                    "system": platform.system(),
                    "machine": platform.machine(),
                    "python_version": platform.python_version()
                },
                "load_average": load_avg,
                "disk": disk_info,
                "warnings": warnings if warnings else None,
                "note": "Limited system metrics available without psutil package"
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    @staticmethod
    def get_application_health() -> Dict[str, Any]:
        """Check application-specific health metrics."""
        return {
            "status": "healthy",
            "version": "1.0.0",
            "environment": "production" if not settings.DEBUG else "development",
            "debug_mode": settings.DEBUG,
            "startup_time": datetime.now(timezone.utc).isoformat(),
            "features": {
                "authentication": True,
                "booking_system": True,
                "user_management": True,
                "session_management": True,
                "reporting": True
            }
        }
    
    @staticmethod
    async def get_comprehensive_health() -> Dict[str, Any]:
        """Get complete system health overview."""
        start_time = time.time()
        
        # Run all health checks
        db_health = await HealthChecker.get_database_health()
        system_health = HealthChecker.get_system_health()
        app_health = HealthChecker.get_application_health()
        
        # Determine overall status
        statuses = [db_health["status"], system_health["status"], app_health["status"]]
        
        if "unhealthy" in statuses:
            overall_status = "unhealthy"
        elif "degraded" in statuses:
            overall_status = "degraded"
        else:
            overall_status = "healthy"
        
        total_time = round((time.time() - start_time) * 1000, 2)
        
        return {
            "status": overall_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "response_time_ms": total_time,
            "checks": {
                "database": db_health,
                "system": system_health,
                "application": app_health
            },
            "summary": {
                "total_checks": 3,
                "healthy_checks": sum(1 for s in statuses if s == "healthy"),
                "degraded_checks": sum(1 for s in statuses if s == "degraded"),
                "unhealthy_checks": sum(1 for s in statuses if s == "unhealthy")
            }
        }