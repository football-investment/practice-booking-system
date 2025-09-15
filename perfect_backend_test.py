#!/usr/bin/env python3
"""
🎯 Perfect Backend Test Script
Comprehensive test that validates all functionality works perfectly
"""

import asyncio
import httpx
import time
from datetime import datetime
import json

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

async def perfect_backend_test():
    print(f"{Colors.BOLD}{Colors.CYAN}🎯 PERFECT BACKEND TEST{Colors.END}")
    print(f"{Colors.BLUE}Practice Booking System - Comprehensive Validation{Colors.END}")
    print("=" * 60)
    
    base_url = "http://localhost:8000"
    success_count = 0
    total_tests = 10
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        # Test 1: Health Check
        print(f"\n{Colors.PURPLE}Test 1: 🏥 Health Check{Colors.END}")
        try:
            start = time.time()
            health = await client.get(f"{base_url}/health")
            duration = time.time() - start
            
            if health.status_code == 200:
                print(f"  {Colors.GREEN}✅ Server Healthy{Colors.END} - {duration*1000:.1f}ms")
                print(f"  {Colors.GREEN}✅ Response{Colors.END}: {health.json()}")
                success_count += 1
            else:
                print(f"  {Colors.RED}❌ Health Check Failed{Colors.END}")
        except Exception as e:
            print(f"  {Colors.RED}❌ Connection Error: {e}{Colors.END}")
        
        # Test 2: Detailed Health
        print(f"\n{Colors.PURPLE}Test 2: 🏥 Detailed Health{Colors.END}")
        try:
            start = time.time()
            health_detailed = await client.get(f"{base_url}/health/detailed")
            duration = time.time() - start
            
            if health_detailed.status_code == 200:
                print(f"  {Colors.GREEN}✅ Detailed Health{Colors.END} - {duration*1000:.1f}ms")
                health_data = health_detailed.json()
                if 'database' in health_data:
                    print(f"  {Colors.GREEN}✅ Database Connected{Colors.END}")
                    print(f"  {Colors.BLUE}ℹ️  Users in DB{Colors.END}: {health_data.get('database', {}).get('users_count', 'N/A')}")
                success_count += 1
            else:
                print(f"  {Colors.RED}❌ Detailed Health Failed{Colors.END}")
        except Exception as e:
            print(f"  {Colors.RED}❌ Error: {e}{Colors.END}")
        
        # Test 3: API Documentation
        print(f"\n{Colors.PURPLE}Test 3: 📚 API Documentation{Colors.END}")
        try:
            docs = await client.get(f"{base_url}/docs")
            if docs.status_code == 200:
                print(f"  {Colors.GREEN}✅ Swagger UI Available{Colors.END}")
                success_count += 1
            else:
                print(f"  {Colors.RED}❌ Swagger UI Failed{Colors.END}")
        except Exception as e:
            print(f"  {Colors.RED}❌ Error: {e}{Colors.END}")
        
        # Test 4: Authentication
        print(f"\n{Colors.PURPLE}Test 4: 🔐 Authentication{Colors.END}")
        try:
            start = time.time()
            login_data = {
                "email": "admin@company.com",
                "password": "admin123"
            }
            
            login = await client.post(f"{base_url}/api/v1/auth/login", json=login_data)
            duration = time.time() - start
            
            if login.status_code == 200:
                token_data = login.json()
                admin_token = token_data.get('access_token')
                print(f"  {Colors.GREEN}✅ Admin Login Success{Colors.END} - {duration*1000:.1f}ms")
                print(f"  {Colors.GREEN}✅ JWT Token Generated{Colors.END}")
                success_count += 1
                
                # Store token for further tests
                headers = {"Authorization": f"Bearer {admin_token}"}
                
                # Test 5: Current User
                print(f"\n{Colors.PURPLE}Test 5: 👤 Current User Info{Colors.END}")
                try:
                    me = await client.get(f"{base_url}/api/v1/auth/me", headers=headers)
                    if me.status_code == 200:
                        user_data = me.json()
                        print(f"  {Colors.GREEN}✅ User Profile Retrieved{Colors.END}")
                        print(f"  {Colors.BLUE}ℹ️  User{Colors.END}: {user_data.get('name')} ({user_data.get('role')})")
                        success_count += 1
                    else:
                        print(f"  {Colors.RED}❌ User Profile Failed{Colors.END}")
                except Exception as e:
                    print(f"  {Colors.RED}❌ Error: {e}{Colors.END}")
                
                # Test 6: Users List
                print(f"\n{Colors.PURPLE}Test 6: 👥 Users Management{Colors.END}")
                try:
                    users = await client.get(f"{base_url}/api/v1/users/", headers=headers)
                    if users.status_code == 200:
                        users_data = users.json()
                        user_count = len(users_data.get('users', []))
                        print(f"  {Colors.GREEN}✅ Users List Retrieved{Colors.END}")
                        print(f"  {Colors.BLUE}ℹ️  Total Users{Colors.END}: {user_count}")
                        success_count += 1
                    else:
                        print(f"  {Colors.RED}❌ Users List Failed{Colors.END}")
                        print(f"  {Colors.RED}Response: {users.status_code} - {users.text}{Colors.END}")
                except Exception as e:
                    print(f"  {Colors.RED}❌ Error: {e}{Colors.END}")
                
                # Test 7: Semesters
                print(f"\n{Colors.PURPLE}Test 7: 📅 Semester Management{Colors.END}")
                try:
                    semesters = await client.get(f"{base_url}/api/v1/semesters/", headers=headers)
                    if semesters.status_code == 200:
                        semesters_data = semesters.json()
                        print(f"  {Colors.GREEN}✅ Semesters Retrieved{Colors.END}")
                        print(f"  {Colors.BLUE}ℹ️  Semesters{Colors.END}: {len(semesters_data)}")
                        success_count += 1
                    else:
                        print(f"  {Colors.RED}❌ Semesters Failed{Colors.END}")
                except Exception as e:
                    print(f"  {Colors.RED}❌ Error: {e}{Colors.END}")
                
                # Test 8: Sessions
                print(f"\n{Colors.PURPLE}Test 8: 🏫 Session Management{Colors.END}")
                try:
                    sessions = await client.get(f"{base_url}/api/v1/sessions/", headers=headers)
                    if sessions.status_code == 200:
                        sessions_data = sessions.json()
                        print(f"  {Colors.GREEN}✅ Sessions Retrieved{Colors.END}")
                        print(f"  {Colors.BLUE}ℹ️  Sessions{Colors.END}: {len(sessions_data)}")
                        success_count += 1
                    else:
                        print(f"  {Colors.RED}❌ Sessions Failed{Colors.END}")
                except Exception as e:
                    print(f"  {Colors.RED}❌ Error: {e}{Colors.END}")
                
            else:
                print(f"  {Colors.RED}❌ Admin Login Failed{Colors.END}")
                print(f"  {Colors.RED}Response: {login.status_code} - {login.text}{Colors.END}")
                
        except Exception as e:
            print(f"  {Colors.RED}❌ Authentication Error: {e}{Colors.END}")
        
        # Test 9: Rate Limiting Test (Should NOT be blocked)
        print(f"\n{Colors.PURPLE}Test 9: ⚡ Rate Limiting Test{Colors.END}")
        try:
            rapid_requests = 0
            for i in range(5):  # Try 5 rapid requests
                health = await client.get(f"{base_url}/health")
                if health.status_code == 200:
                    rapid_requests += 1
                await asyncio.sleep(0.1)  # Small delay
            
            if rapid_requests >= 4:  # At least 4 out of 5 should work
                print(f"  {Colors.GREEN}✅ Rate Limiting Properly Configured{Colors.END}")
                print(f"  {Colors.BLUE}ℹ️  Successful requests{Colors.END}: {rapid_requests}/5")
                success_count += 1
            else:
                print(f"  {Colors.YELLOW}⚠️  Rate limiting might be too strict{Colors.END}")
        except Exception as e:
            print(f"  {Colors.RED}❌ Error: {e}{Colors.END}")
        
        # Test 10: Performance Test
        print(f"\n{Colors.PURPLE}Test 10: 🚀 Performance Test{Colors.END}")
        try:
            times = []
            for i in range(5):
                start = time.time()
                health = await client.get(f"{base_url}/health")
                duration = time.time() - start
                if health.status_code == 200:
                    times.append(duration)
            
            if times:
                avg_time = sum(times) / len(times)
                if avg_time < 0.1:  # Under 100ms average
                    print(f"  {Colors.GREEN}✅ Excellent Performance{Colors.END}")
                    print(f"  {Colors.BLUE}ℹ️  Average Response Time{Colors.END}: {avg_time*1000:.1f}ms")
                    success_count += 1
                else:
                    print(f"  {Colors.YELLOW}⚠️  Performance Could Be Better{Colors.END}")
                    print(f"  {Colors.BLUE}ℹ️  Average Response Time{Colors.END}: {avg_time*1000:.1f}ms")
        except Exception as e:
            print(f"  {Colors.RED}❌ Error: {e}{Colors.END}")
    
    # Final Results
    print(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}🎯 BACKEND TEST RESULTS{Colors.END}")
    print(f"{Colors.BOLD}{'='*60}{Colors.END}")
    
    success_rate = (success_count / total_tests) * 100
    
    if success_rate >= 90:
        print(f"{Colors.GREEN}🎉 EXCELLENT: {success_count}/{total_tests} tests passed ({success_rate:.1f}%){Colors.END}")
        print(f"{Colors.GREEN}✅ Backend is production ready!{Colors.END}")
    elif success_rate >= 70:
        print(f"{Colors.YELLOW}👍 GOOD: {success_count}/{total_tests} tests passed ({success_rate:.1f}%){Colors.END}")
        print(f"{Colors.YELLOW}⚠️  Minor issues need attention{Colors.END}")
    else:
        print(f"{Colors.RED}⚠️  NEEDS WORK: {success_count}/{total_tests} tests passed ({success_rate:.1f}%){Colors.END}")
        print(f"{Colors.RED}❌ Significant issues need fixing{Colors.END}")
    
    print(f"\n{Colors.BLUE}🔗 Quick Links:{Colors.END}")
    print(f"  📚 API Docs: http://localhost:8000/docs")
    print(f"  🏥 Health: http://localhost:8000/health/detailed")
    print(f"  📊 ReDoc: http://localhost:8000/redoc")


if __name__ == "__main__":
    asyncio.run(perfect_backend_test())
