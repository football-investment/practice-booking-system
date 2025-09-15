
        # DEVELOPMENT-FRIENDLY RATE LIMITING PATCH
        # Dinamikus rate limiting beállítás
        
        import os
        import sys
        from typing import Optional
        
        def is_development_mode() -> bool:
            """Detect development/testing mode"""
            return (
                os.getenv("ENVIRONMENT", "development").lower() in ("development", "dev", "test") or
                os.getenv("DEBUG", "").lower() in ("1", "true", "yes") or
                "pytest" in sys.modules or
                os.getenv("TESTING", "").lower() in ("1", "true", "yes") or
                "validation" in " ".join(sys.argv).lower() or
                "--reload" in sys.argv
            )
        
        # Dynamic rate limiting settings
        DEVELOPMENT_MODE = is_development_mode()
        
        # Permissive settings for development/testing
        if DEVELOPMENT_MODE:
            RATE_LIMIT_CALLS: int = 1000
            RATE_LIMIT_WINDOW_SECONDS: int = 60
            LOGIN_RATE_LIMIT_CALLS: int = 100
            LOGIN_RATE_LIMIT_WINDOW_SECONDS: int = 60
            ENABLE_RATE_LIMITING: bool = False  # Disabled in development
        else:
            # Production settings
            RATE_LIMIT_CALLS: int = 100
            RATE_LIMIT_WINDOW_SECONDS: int = 60
            LOGIN_RATE_LIMIT_CALLS: int = 10
            LOGIN_RATE_LIMIT_WINDOW_SECONDS: int = 60
            ENABLE_RATE_LIMITING: bool = True  # Enabled in production
        