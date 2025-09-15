#!/usr/bin/env python3
"""
⚡ Practice Booking System - Performance Benchmark Script
Detailed performance testing and load analysis
"""

import asyncio
import httpx
import time
import statistics
from datetime import datetime
import json

class PerformanceBenchmark:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = {}
        
    async def benchmark_endpoint(self, name: str, method: str, endpoint: str, headers: dict = None, json_data: dict = None, iterations: int = 100):
        """Benchmark a specific endpoint"""
        print(f"🔄 Benchmarking {name} ({iterations} iterations)...")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            times = []
            successes = 0
            errors = 0
            
            for i in range(iterations):
                start_time = time.time()
                try:
                    response = await client.request(
                        method, 
                        f"{self.base_url}{endpoint}",
                        headers=headers,
                        json=json_data
                    )
                    duration = time.time() - start_time
                    times.append(duration)
                    
                    if response.status_code < 400:
                        successes += 1
                    else:
                        errors += 1
                        
                except Exception as e:
                    duration = time.time() - start_time
                    times.append(duration)
                    errors += 1
            
            # Calculate statistics
            if times:
                avg_time = statistics.mean(times)
                median_time = statistics.median(times)
                min_time = min(times)
                max_time = max(times)
                p95_time = sorted(times)[int(0.95 * len(times))]
                p99_time = sorted(times)[int(0.99 * len(times))]
            else:
                avg_time = median_time = min_time = max_time = p95_time = p99_time = 0
            
            success_rate = (successes / iterations) * 100
            
            self.results[name] = {
                "endpoint": endpoint,
                "method": method,
                "iterations": iterations,
                "success_rate": success_rate,
                "avg_time_ms": avg_time * 1000,
                "median_time_ms": median_time * 1000,
                "min_time_ms": min_time * 1000,
                "max_time_ms": max_time * 1000,
                "p95_time_ms": p95_time * 1000,
                "p99_time_ms": p99_time * 1000,
                "requests_per_second": 1 / avg_time if avg_time > 0 else 0
            }
            
            print(f"  ✅ Avg: {avg_time*1000:.1f}ms | P95: {p95_time*1000:.1f}ms | Success: {success_rate:.1f}%")
    
    async def run_benchmarks(self):
        """Run comprehensive performance benchmarks"""
        print("⚡ Starting Performance Benchmarks")
        print("=" * 50)
        
        # Get admin token first
        admin_token = await self.get_admin_token()
        headers = {"Authorization": f"Bearer {admin_token}"} if admin_token else {}
        
        # Benchmark critical endpoints
        endpoints = [
            ("Health Check", "GET", "/health", None, None, 200),
            ("Root Endpoint", "GET", "/", None, None, 100),
            ("Admin Login", "POST", "/api/v1/auth/login", None, {
                "email": "admin@company.com", 
                "password": "admin123"
            }, 50),
            ("List Users", "GET", "/api/v1/users/", headers, None, 100),
            ("List Semesters", "GET", "/api/v1/semesters/", headers, None, 100),
            ("List Sessions", "GET", "/api/v1/sessions/", headers, None, 100),
            ("Get Current User", "GET", "/api/v1/auth/me", headers, None, 100),
            ("OpenAPI Schema", "GET", "/openapi.json", None, None, 50),
        ]
        
        for name, method, endpoint, req_headers, json_data, iterations in endpoints:
            await self.benchmark_endpoint(name, method, endpoint, req_headers, json_data, iterations)
        
        # Load test - concurrent requests
        await self.load_test()
        
        # Generate report
        self.generate_performance_report()
    
    async def get_admin_token(self):
        """Get admin authentication token"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/auth/login",
                    json={"email": "admin@company.com", "password": "admin123"}
                )
                if response.status_code == 200:
                    return response.json().get("access_token")
        except:
            pass
        return None
    
    async def load_test(self):
        """Perform load testing with concurrent requests"""
        print("🚀 Load Testing (50 concurrent requests to health endpoint)...")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            start_time = time.time()
            
            # Create 50 concurrent requests
            tasks = []
            for _ in range(50):
                task = client.get(f"{self.base_url}/health")
                tasks.append(task)
            
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            total_time = time.time() - start_time
            
            successes = sum(1 for r in responses if hasattr(r, 'status_code') and r.status_code == 200)
            errors = 50 - successes
            
            self.results["Load Test"] = {
                "endpoint": "/health",
                "method": "GET",
                "concurrent_requests": 50,
                "total_time_s": total_time,
                "requests_per_second": 50 / total_time,
                "success_rate": (successes / 50) * 100,
                "avg_time_ms": (total_time / 50) * 1000
            }
            
            print(f"  ✅ 50 requests in {total_time:.2f}s | RPS: {50/total_time:.1f} | Success: {(successes/50)*100:.1f}%")
    
    def generate_performance_report(self):
        """Generate comprehensive performance report"""
        print("\n" + "=" * 50)
        print("📊 PERFORMANCE BENCHMARK RESULTS")
        print("=" * 50)
        
        # Summary statistics
        all_avg_times = [r["avg_time_ms"] for r in self.results.values() if "avg_time_ms" in r]
        all_success_rates = [r["success_rate"] for r in self.results.values() if "success_rate" in r]
        
        if all_avg_times:
            overall_avg = statistics.mean(all_avg_times)
            overall_success = statistics.mean(all_success_rates)
            
            print(f"🎯 Overall Performance:")
            print(f"  • Average Response Time: {overall_avg:.1f}ms")
            print(f"  • Overall Success Rate: {overall_success:.1f}%")
            print(f"  • Endpoints Tested: {len(self.results)}")
        
        print(f"\n📈 Detailed Results:")
        for name, data in self.results.items():
            if "avg_time_ms" in data:
                print(f"  {name}:")
                print(f"    • Avg: {data['avg_time_ms']:.1f}ms")
                print(f"    • P95: {data['p95_time_ms']:.1f}ms") 
                print(f"    • Max: {data['max_time_ms']:.1f}ms")
                print(f"    • RPS: {data['requests_per_second']:.1f}")
                print(f"    • Success: {data['success_rate']:.1f}%")
            elif "concurrent_requests" in data:
                print(f"  {name}:")
                print(f"    • Concurrent Requests: {data['concurrent_requests']}")
                print(f"    • Total Time: {data['total_time_s']:.2f}s")
                print(f"    • RPS: {data['requests_per_second']:.1f}")
                print(f"    • Success: {data['success_rate']:.1f}%")
        
        # Performance classification
        print(f"\n🏆 Performance Classification:")
        if overall_avg < 50:
            print("  ⚡ EXCELLENT - Sub-50ms average response time")
        elif overall_avg < 100:
            print("  ✅ GOOD - Sub-100ms average response time")
        elif overall_avg < 200:
            print("  ⚠️  ACCEPTABLE - Sub-200ms average response time")
        else:
            print("  ❌ NEEDS IMPROVEMENT - Over 200ms average response time")
        
        # Save detailed results
        timestamp = datetime.now().isoformat()
        report_data = {
            "timestamp": timestamp,
            "overall_avg_ms": overall_avg,
            "overall_success_rate": overall_success,
            "endpoints_tested": len(self.results),
            "results": self.results
        }
        
        with open("performance_benchmark_results.json", "w") as f:
            json.dump(report_data, f, indent=2)
        
        print(f"\n💾 Results saved to: performance_benchmark_results.json")

async def main():
    benchmark = PerformanceBenchmark()
    await benchmark.run_benchmarks()

if __name__ == "__main__":
    asyncio.run(main())