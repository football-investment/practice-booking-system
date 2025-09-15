#!/usr/bin/env python3
"""
Validate production vs test configuration.
"""

import os
import sys
import time
import requests
from pathlib import Path


def test_production_rate_limiting():
    """Test that rate limiting works in production mode"""
    print("🔒 Testing production rate limiting...")
    
    # Start server in production mode
    os.environ.pop("TESTING", None)  # Remove testing flag
    
    # Import after environment setup
    sys.path.insert(0, str(Path(__file__).parent))
    from app.config import settings
    from app.middleware.security import RateLimitMiddleware
    
    print(f"Environment: {settings.ENVIRONMENT}")
    print(f"Testing mode: {settings.TESTING}")
    print(f"Rate limiting enabled: {settings.ENABLE_RATE_LIMITING}")
    print(f"Security headers enabled: {settings.ENABLE_SECURITY_HEADERS}")
    print(f"Structured logging enabled: {settings.ENABLE_STRUCTURED_LOGGING}")
    
    if settings.TESTING:
        print("❌ ERROR: Should not be in testing mode for production validation")
        return False
    
    if not settings.ENABLE_RATE_LIMITING:
        print("❌ ERROR: Rate limiting should be enabled in production")
        return False
    
    print("✅ Production configuration validated")
    return True


def test_testing_configuration():
    """Test that testing mode disables production middleware"""
    print("\n🧪 Testing test configuration...")
    
    # Set testing environment
    os.environ["TESTING"] = "true"
    
    # Force reload of settings
    if 'app.config' in sys.modules:
        del sys.modules['app.config']
    
    from app.config import settings
    
    print(f"Environment: {settings.ENVIRONMENT}")
    print(f"Testing mode: {settings.TESTING}")
    print(f"Rate limiting enabled: {settings.ENABLE_RATE_LIMITING}")
    print(f"Security headers enabled: {settings.ENABLE_SECURITY_HEADERS}")
    print(f"Structured logging enabled: {settings.ENABLE_STRUCTURED_LOGGING}")
    
    if not settings.TESTING:
        print("❌ ERROR: Should be in testing mode")
        return False
    
    if settings.ENABLE_RATE_LIMITING:
        print("❌ ERROR: Rate limiting should be disabled in testing")
        return False
    
    print("✅ Testing configuration validated")
    return True


def test_rate_limiting_bypass():
    """Test that multiple rapid requests work in testing mode but are limited in production"""
    print("\n⚡ Testing rate limiting behavior...")
    
    # This would require starting separate server instances
    # For now, just validate configuration logic
    
    # Production settings
    os.environ.pop("TESTING", None)
    if 'app.config' in sys.modules:
        del sys.modules['app.config']
    
    from app.config import settings as prod_settings
    
    # Test settings  
    os.environ["TESTING"] = "true"
    if 'app.config' in sys.modules:
        del sys.modules['app.config']
    
    from app.config import settings as test_settings
    
    print(f"Production rate limiting: {prod_settings.ENABLE_RATE_LIMITING}")
    print(f"Testing rate limiting: {test_settings.ENABLE_RATE_LIMITING}")
    
    if prod_settings.ENABLE_RATE_LIMITING == test_settings.ENABLE_RATE_LIMITING:
        print("❌ ERROR: Rate limiting should be different between production and testing")
        return False
    
    print("✅ Rate limiting behavior validated")
    return True


def main():
    """Run all validation tests"""
    print("=" * 60)
    print("🔧 PRODUCTION CONFIGURATION VALIDATION")
    print("=" * 60)
    
    tests = [
        ("Production Configuration", test_production_rate_limiting),
        ("Testing Configuration", test_testing_configuration),
        ("Rate Limiting Behavior", test_rate_limiting_bypass),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ ERROR in {test_name}: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 VALIDATION SUMMARY")
    print("=" * 60)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    success_rate = (passed / len(results)) * 100
    print(f"\nSuccess rate: {passed}/{len(results)} ({success_rate:.1f}%)")
    
    if passed == len(results):
        print("🎉 All configuration validations passed!")
        return True
    else:
        print("⚠️ Some validations failed")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)