#!/usr/bin/env python3
"""
🔍 INDEPENDENT BACKEND VERIFICATION SCRIPT
CRITICAL: Verify Claude Code claims independently
DO NOT TRUST PREVIOUS SUCCESS REPORTS
"""

import asyncio
import httpx
import json
import time
import traceback
import sys
from datetime import datetime
from typing import Dict, List, Any

class BackendVerifier:
    """Independent verification of backend functionality"""
    
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.admin_token = None
        self.results = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "errors": [],
            "performance": {},
            "evidence": {}
        }
    
    async def run_verification(self):
        """Run complete verification suite"""
        print("🔍 INDEPENDENT BACKEND VERIFICATION")
        print("=" * 60)
        print("⚠️  WARNING: This verification ignores all previous Claude Code claims")
        print("⚠️  WARNING: Only actual test results will be trusted")
        print("=" * 60)
        
        tests = [
            ("Server Health Check", self.test_server_health),
            ("Database Connection", self.test_database_connection),
            ("Authentication System", self.test_authentication),
            ("User Management API", self.test_user_management),
            ("Semester Management", self.test_semester_management), 
            ("Session Management", self.test_session_management),
            ("Booking System", self.test_booking_system),
            ("Permission System", self.test_permissions),
            ("Performance Test", self.test_performance),
            ("Error Handling", self.test_error_handling)
        ]
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            self.client = client
            
            for test_name, test_func in tests:
                await self.run_single_test(test_name, test_func)
        
        self.generate_report()
    
    async def run_single_test(self, test_name: str, test_func):
        """Run single test with error handling"""
        self.results["total_tests"] += 1
        
        print(f"\n📋 Testing: {test_name}")
        print("-" * 40)
        
        try:
            start_time = time.time()
            result = await test_func()
            duration = time.time() - start_time
            
            if result["success"]:
                print(f"✅ PASS: {test_name} ({duration:.2f}s)")
                self.results["passed"] += 1
            else:
                print(f"❌ FAIL: {test_name}")
                print(f"   Error: {result['error']}")
                self.results["failed"] += 1
                self.results["errors"].append({
                    "test": test_name,
                    "error": result["error"]
                })
            
            self.results["evidence"][test_name] = result
            
        except Exception as e:
            print(f"💥 EXCEPTION: {test_name}")
            print(f"   Exception: {str(e)}")
            traceback.print_exc()
            self.results["failed"] += 1
            self.results["errors"].append({
                "test": test_name,
                "error": f"Exception: {str(e)}"
            })
    
    async def test_server_health(self) -> Dict:
        """Test if server is actually running and responding"""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✓ Health endpoint: {response.status_code}")
                print(f"   ✓ Response time: {response.elapsed.total_seconds()*1000:.1f}ms")
                print(f"   ✓ Response data: {data}")
                
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds()*1000,
                    "data": data
                }
            else:
                return {
                    "success": False,
                    "error": f"Health check failed: {response.status_code}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Server connection failed: {str(e)}"
            }
    
    async def test_database_connection(self) -> Dict:
        """Test database connectivity through detailed health endpoint"""
        try:
            response = await self.client.get(f"{self.base_url}/health/detailed")
            
            if response.status_code == 200:
                data = response.json()
                
                if "database" in data:
                    db_info = data["database"]
                    print(f"   ✓ Database endpoint: {response.status_code}")
                    print(f"   ✓ Users count: {db_info.get('users_count', 'N/A')}")
                    print(f"   ✓ Sessions count: {db_info.get('sessions_count', 'N/A')}")
                    
                    return {
                        "success": True,
                        "database_info": db_info
                    }
                else:
                    return {
                        "success": False,
                        "error": "No database info in health response"
                    }
            else:
                return {
                    "success": False,
                    "error": f"Database health failed: {response.status_code}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Database test failed: {str(e)}"
            }
    
    async def test_authentication(self) -> Dict:
        """Test authentication system"""
        try:
            login_data = {
                "email": "admin@company.com",
                "password": "admin123"
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/v1/auth/login",
                json=login_data
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if "access_token" in data:
                    self.admin_token = data["access_token"]
                    print(f"   ✓ Login successful: {response.status_code}")
                    print(f"   ✓ Token length: {len(self.admin_token)}")
                    print(f"   ✓ Token type: {data.get('token_type', 'N/A')}")
                    
                    # Test token validity
                    auth_headers = {"Authorization": f"Bearer {self.admin_token}"}
                    me_response = await self.client.get(
                        f"{self.base_url}/api/v1/auth/me",
                        headers=auth_headers
                    )
                    
                    if me_response.status_code == 200:
                        user_data = me_response.json()
                        print(f"   ✓ Token valid: User {user_data.get('name')} ({user_data.get('role')})")
                        
                        return {
                            "success": True,
                            "token_length": len(self.admin_token),
                            "user_data": user_data
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"Token validation failed: {me_response.status_code}"
                        }
                else:
                    return {
                        "success": False,
                        "error": "No access_token in login response"
                    }
            else:
                return {
                    "success": False,
                    "error": f"Login failed: {response.status_code} - {response.text}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Authentication test failed: {str(e)}"
            }
    
    async def test_user_management(self) -> Dict:
        """Test user management endpoints"""
        if not self.admin_token:
            return {"success": False, "error": "No admin token available"}
        
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            
            # Test user list
            response = await self.client.get(
                f"{self.base_url}/api/v1/users/",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                user_count = len(data.get("users", []))
                print(f"   ✓ Users list: {response.status_code}")
                print(f"   ✓ User count: {user_count}")
                
                return {
                    "success": True,
                    "user_count": user_count,
                    "users_data": data
                }
            else:
                return {
                    "success": False,
                    "error": f"Users list failed: {response.status_code}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"User management test failed: {str(e)}"
            }
    
    async def test_semester_management(self) -> Dict:
        """Test semester management"""
        if not self.admin_token:
            return {"success": False, "error": "No admin token available"}
        
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            
            response = await self.client.get(
                f"{self.base_url}/api/v1/semesters/",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                semester_count = len(data) if isinstance(data, list) else 0
                print(f"   ✓ Semesters list: {response.status_code}")
                print(f"   ✓ Semester count: {semester_count}")
                
                return {
                    "success": True,
                    "semester_count": semester_count
                }
            else:
                return {
                    "success": False,
                    "error": f"Semesters list failed: {response.status_code}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Semester test failed: {str(e)}"
            }
    
    async def test_session_management(self) -> Dict:
        """Test session management"""
        if not self.admin_token:
            return {"success": False, "error": "No admin token available"}
        
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            
            response = await self.client.get(
                f"{self.base_url}/api/v1/sessions/",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                session_count = len(data) if isinstance(data, list) else 0
                print(f"   ✓ Sessions list: {response.status_code}")
                print(f"   ✓ Session count: {session_count}")
                
                return {
                    "success": True,
                    "session_count": session_count
                }
            else:
                return {
                    "success": False,
                    "error": f"Sessions list failed: {response.status_code}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Session test failed: {str(e)}"
            }
    
    async def test_booking_system(self) -> Dict:
        """Test booking functionality"""
        if not self.admin_token:
            return {"success": False, "error": "No admin token available"}
        
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            
            # Test getting bookings (user's own bookings)
            response = await self.client.get(
                f"{self.base_url}/api/v1/bookings/me",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                booking_count = len(data) if isinstance(data, list) else 0
                print(f"   ✓ Bookings endpoint: {response.status_code}")
                print(f"   ✓ Booking count: {booking_count}")
                
                return {
                    "success": True,
                    "booking_count": booking_count
                }
            else:
                return {
                    "success": False,
                    "error": f"Bookings endpoint failed: {response.status_code}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Booking test failed: {str(e)}"
            }
    
    async def test_permissions(self) -> Dict:
        """Test permission system"""
        try:
            # Test unauthorized access
            response = await self.client.get(f"{self.base_url}/api/v1/users/")
            
            if response.status_code == 401:
                print(f"   ✓ Unauthorized access blocked: {response.status_code}")
                
                return {
                    "success": True,
                    "unauthorized_blocked": True
                }
            else:
                return {
                    "success": False,
                    "error": f"Unauthorized access not blocked: {response.status_code}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Permission test failed: {str(e)}"
            }
    
    async def test_performance(self) -> Dict:
        """Test basic performance"""
        try:
            times = []
            
            for i in range(5):
                start = time.time()
                response = await self.client.get(f"{self.base_url}/health")
                duration = (time.time() - start) * 1000
                
                if response.status_code == 200:
                    times.append(duration)
            
            if times:
                avg_time = sum(times) / len(times)
                print(f"   ✓ Average response time: {avg_time:.1f}ms")
                print(f"   ✓ Min time: {min(times):.1f}ms")
                print(f"   ✓ Max time: {max(times):.1f}ms")
                
                return {
                    "success": True,
                    "avg_response_time": avg_time,
                    "min_time": min(times),
                    "max_time": max(times)
                }
            else:
                return {
                    "success": False,
                    "error": "No successful performance tests"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Performance test failed: {str(e)}"
            }
    
    async def test_error_handling(self) -> Dict:
        """Test error handling"""
        try:
            # Test invalid endpoint
            response = await self.client.get(f"{self.base_url}/api/v1/nonexistent")
            
            if response.status_code == 404:
                print(f"   ✓ 404 errors handled: {response.status_code}")
                
                # Test invalid JSON
                response = await self.client.post(
                    f"{self.base_url}/api/v1/auth/login",
                    data="invalid json"
                )
                
                if response.status_code in [400, 422]:
                    print(f"   ✓ Invalid JSON handled: {response.status_code}")
                    
                    return {
                        "success": True,
                        "handles_404": True,
                        "handles_invalid_json": True
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Invalid JSON not handled properly: {response.status_code}"
                    }
            else:
                return {
                    "success": False,
                    "error": f"404 not handled properly: {response.status_code}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Error handling test failed: {str(e)}"
            }
    
    def generate_report(self):
        """Generate final verification report"""
        print("\n" + "=" * 60)
        print("🔍 INDEPENDENT BACKEND VERIFICATION RESULTS")
        print("=" * 60)
        
        success_rate = (self.results["passed"] / self.results["total_tests"]) * 100
        
        print(f"📊 Total Tests: {self.results['total_tests']}")
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        print(f"📈 Success Rate: {success_rate:.1f}%")
        
        if self.results["errors"]:
            print(f"\n🚨 FAILURES:")
            for error in self.results["errors"]:
                print(f"   ❌ {error['test']}: {error['error']}")
        
        # Determine overall status
        if success_rate >= 90:
            print(f"\n🎉 VERDICT: Backend is GENUINELY FUNCTIONAL")
            print(f"✅ Ready for minimal frontend development")
        elif success_rate >= 70:
            print(f"\n⚠️  VERDICT: Backend has ISSUES but core works")
            print(f"🔧 Needs fixes before frontend development")
        else:
            print(f"\n🚨 VERDICT: Backend has SERIOUS PROBLEMS")
            print(f"❌ NOT ready for frontend development")
        
        # Save results to file
        with open("backend_verification_results.json", "w") as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"\n📁 Detailed results saved to: backend_verification_results.json")
        
        return success_rate


async def main():
    """Run independent backend verification"""
    verifier = BackendVerifier()
    await verifier.run_verification()


if __name__ == "__main__":
    asyncio.run(main())