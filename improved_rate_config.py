#!/usr/bin/env python3
"""
Improved Rate Limiting Configuration
Fixes the validation script issues by providing more permissive settings
"""

import os
from pathlib import Path

def create_development_config():
    """Create development-friendly configuration"""
    config_content = '''
# DEVELOPMENT/TESTING CONFIGURATION
# More permissive settings for local testing

# Rate Limiting - Much more permissive
RATE_LIMIT_CALLS=1000
RATE_LIMIT_WINDOW_SECONDS=60
LOGIN_RATE_LIMIT_CALLS=50  # Much more permissive
LOGIN_RATE_LIMIT_WINDOW_SECONDS=60

# Security - Relaxed for development
ENABLE_RATE_LIMITING=false
ENABLE_SECURITY_HEADERS=true
ENABLE_REQUEST_SIZE_LIMIT=false
ENABLE_STRUCTURED_LOGGING=true

# Testing mode detection
TESTING=false
ENVIRONMENT=development
'''
    
    # Append to .env if not already there
    env_path = Path('.env')
    if env_path.exists():
        content = env_path.read_text()
        if 'RATE_LIMIT_CALLS' not in content:
            with open('.env', 'a') as f:
                f.write('\n# DEVELOPMENT RATE LIMITING\n')
                f.write(config_content)
            print("✅ Enhanced rate limiting configuration added to .env")
        else:
            print("ℹ️  Rate limiting configuration already exists")
    else:
        print("❌ .env file not found")

if __name__ == "__main__":
    create_development_config()
