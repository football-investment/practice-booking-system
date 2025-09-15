#!/usr/bin/env python3
"""
Production-ready server startup script with health validation.
"""

import os
import sys
import time
import signal
import subprocess
import requests
import json
from pathlib import Path
from typing import Optional


class ServerManager:
    def __init__(self, host="localhost", port=8000):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self.process: Optional[subprocess.Popen] = None
        self.project_root = Path(__file__).parent
        
    def start_server(self) -> bool:
        """Start the uvicorn server"""
        print(f"🚀 Starting server at {self.base_url}...")
        
        # Change to project directory
        os.chdir(self.project_root)
        
        # Start uvicorn server
        cmd = [
            sys.executable, "-m", "uvicorn",
            "app.main:app",
            "--host", self.host,
            "--port", str(self.port),
            "--reload"  # Enable hot reloading for development
        ]
        
        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            print(f"✅ Server process started (PID: {self.process.pid})")
            return True
            
        except Exception as e:
            print(f"❌ Failed to start server: {e}")
            return False
    
    def wait_for_server(self, timeout=30) -> bool:
        """Wait for server to be ready"""
        print(f"⏳ Waiting for server to be ready (timeout: {timeout}s)...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{self.base_url}/", timeout=2)
                if response.status_code == 200:
                    print("✅ Server is ready!")
                    return True
            except requests.ConnectionError:
                pass
            except Exception as e:
                print(f"⚠️  Unexpected error while checking server: {e}")
            
            time.sleep(1)
        
        print("❌ Server failed to start within timeout")
        return False
    
    def validate_health_endpoints(self) -> bool:
        """Test all health endpoints"""
        print("\n🏥 Validating health endpoints...")
        
        endpoints = [
            ("/health", "Basic health check"),
            ("/health/detailed", "Detailed health check"),
            ("/health/ready", "Readiness probe"),
            ("/health/live", "Liveness probe")
        ]
        
        all_passed = True
        
        for endpoint, description in endpoints:
            try:
                url = f"{self.base_url}{endpoint}"
                response = requests.get(url, timeout=5)
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ {description}: {endpoint}")
                    print(f"   Status: {response.status_code}")
                    print(f"   Response: {json.dumps(data, indent=2)[:100]}...")
                else:
                    print(f"❌ {description}: {endpoint}")
                    print(f"   Status: {response.status_code}")
                    print(f"   Response: {response.text[:100]}...")
                    all_passed = False
                    
            except Exception as e:
                print(f"❌ {description}: {endpoint}")
                print(f"   Error: {e}")
                all_passed = False
            
            print()  # Empty line for readability
        
        return all_passed
    
    def validate_api_endpoints(self) -> bool:
        """Test key API endpoints"""
        print("🔧 Validating key API endpoints...")
        
        try:
            # Test root endpoint
            response = requests.get(f"{self.base_url}/", timeout=5)
            if response.status_code == 200:
                print("✅ Root endpoint working")
                root_data = response.json()
                print(f"   API: {root_data.get('message')}")
                print(f"   Version: {root_data.get('version')}")
            else:
                print(f"❌ Root endpoint failed: {response.status_code}")
                return False
            
            # Test OpenAPI docs endpoint (FastAPI default is /docs)
            docs_url = f"{self.base_url}/docs"
            response = requests.get(docs_url, timeout=5)
            if response.status_code == 200:
                print("✅ API documentation accessible")
            else:
                print(f"❌ API docs failed: {response.status_code}")
                return False
            
            return True
            
        except Exception as e:
            print(f"❌ API validation error: {e}")
            return False
    
    def stop_server(self):
        """Stop the server gracefully"""
        if self.process:
            print(f"\n🛑 Stopping server (PID: {self.process.pid})...")
            
            try:
                # Try graceful shutdown first
                self.process.terminate()
                
                # Wait for graceful shutdown
                try:
                    self.process.wait(timeout=10)
                    print("✅ Server stopped gracefully")
                except subprocess.TimeoutExpired:
                    # Force kill if not stopped gracefully
                    print("⚠️  Forcefully killing server...")
                    self.process.kill()
                    self.process.wait()
                    print("✅ Server killed")
                    
            except Exception as e:
                print(f"❌ Error stopping server: {e}")
        else:
            print("ℹ️  No server process to stop")
    
    def run_production_check(self) -> bool:
        """Run complete production readiness check"""
        print("=" * 60)
        print("🏭 PRODUCTION READINESS CHECK")
        print("=" * 60)
        
        # Start server
        if not self.start_server():
            return False
        
        # Wait for server to be ready
        if not self.wait_for_server():
            self.stop_server()
            return False
        
        # Validate health endpoints
        health_ok = self.validate_health_endpoints()
        
        # Validate API endpoints
        api_ok = self.validate_api_endpoints()
        
        # Print summary
        print("=" * 60)
        print("📊 VALIDATION SUMMARY")
        print("=" * 60)
        print(f"Health endpoints: {'✅ PASS' if health_ok else '❌ FAIL'}")
        print(f"API endpoints: {'✅ PASS' if api_ok else '❌ FAIL'}")
        
        overall_status = health_ok and api_ok
        print(f"\nOverall status: {'✅ PRODUCTION READY' if overall_status else '❌ ISSUES FOUND'}")
        
        return overall_status


def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully"""
    print("\n🛑 Received interrupt signal...")
    if hasattr(signal_handler, 'server_manager'):
        signal_handler.server_manager.stop_server()
    sys.exit(0)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Practice Booking System Server Manager")
    parser.add_argument("--host", default="localhost", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--check", action="store_true", help="Run production readiness check and exit")
    
    args = parser.parse_args()
    
    # Create server manager
    server_manager = ServerManager(host=args.host, port=args.port)
    
    # Set up signal handling
    signal_handler.server_manager = server_manager
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    if args.check:
        # Run production check and exit
        success = server_manager.run_production_check()
        server_manager.stop_server()
        sys.exit(0 if success else 1)
    else:
        # Start server and keep it running
        if server_manager.start_server() and server_manager.wait_for_server():
            print(f"\n🎉 Server is running at {server_manager.base_url}")
            print("📖 API Documentation: /docs")
            print("🏥 Health Check: /health")
            print("\nPress Ctrl+C to stop the server...")
            
            try:
                # Keep the script running
                server_manager.process.wait()
            except KeyboardInterrupt:
                pass
            finally:
                server_manager.stop_server()
        else:
            sys.exit(1)


if __name__ == "__main__":
    main()