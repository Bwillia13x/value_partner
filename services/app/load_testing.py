"""Load testing and performance validation tools"""
import asyncio
import aiohttp
import time
import statistics
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import random
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class LoadTestConfig:
    """Configuration for load testing"""
    base_url: str
    concurrent_users: int
    test_duration: int  # seconds
    ramp_up_time: int   # seconds
    endpoints: List[Dict[str, Any]]
    auth_token: Optional[str] = None
    headers: Optional[Dict[str, str]] = None

@dataclass
class LoadTestResult:
    """Result of load testing"""
    endpoint: str
    method: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    p95_response_time: float
    p99_response_time: float
    requests_per_second: float
    error_rate: float
    errors: List[str]
    timestamp: datetime

@dataclass
class LoadTestSummary:
    """Summary of all load test results"""
    test_name: str
    config: LoadTestConfig
    results: List[LoadTestResult]
    total_duration: float
    overall_success_rate: float
    overall_avg_response_time: float
    overall_requests_per_second: float
    timestamp: datetime

class LoadTestRunner:
    """Load testing runner for API endpoints"""
    
    def __init__(self, config: LoadTestConfig):
        self.config = config
        self.results = []
        self.session = None
        
    async def run_load_test(self, test_name: str = "Load Test") -> LoadTestSummary:
        """Run the complete load test"""
        start_time = time.time()
        
        logger.info(f"Starting load test: {test_name}")
        logger.info(f"Config: {self.config.concurrent_users} users, {self.config.test_duration}s duration")
        
        # Create session with timeout
        timeout = aiohttp.ClientTimeout(total=30)
        connector = aiohttp.TCPConnector(limit=self.config.concurrent_users * 2)
        
        async with aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers=self.config.headers
        ) as session:
            self.session = session
            
            # Run tests for each endpoint
            tasks = []
            for endpoint_config in self.config.endpoints:
                task = asyncio.create_task(
                    self._test_endpoint(endpoint_config)
                )
                tasks.append(task)
            
            # Wait for all endpoint tests to complete
            await asyncio.gather(*tasks)
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Calculate overall statistics
        overall_success_rate = self._calculate_overall_success_rate()
        overall_avg_response_time = self._calculate_overall_avg_response_time()
        overall_rps = self._calculate_overall_requests_per_second()
        
        summary = LoadTestSummary(
            test_name=test_name,
            config=self.config,
            results=self.results,
            total_duration=total_duration,
            overall_success_rate=overall_success_rate,
            overall_avg_response_time=overall_avg_response_time,
            overall_requests_per_second=overall_rps,
            timestamp=datetime.utcnow()
        )
        
        logger.info(f"Load test completed in {total_duration:.2f}s")
        logger.info(f"Overall success rate: {overall_success_rate:.2f}%")
        logger.info(f"Overall avg response time: {overall_avg_response_time:.2f}ms")
        
        return summary
    
    async def _test_endpoint(self, endpoint_config: Dict[str, Any]):
        """Test a single endpoint with concurrent requests"""
        endpoint = endpoint_config["endpoint"]
        method = endpoint_config.get("method", "GET")
        payload = endpoint_config.get("payload", {})
        
        logger.info(f"Testing endpoint: {method} {endpoint}")
        
        # Track response times and errors
        response_times = []
        errors = []
        successful_requests = 0
        failed_requests = 0
        
        # Calculate request rate
        requests_per_user = max(1, self.config.test_duration // self.config.concurrent_users)
        
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(self.config.concurrent_users)
        
        async def make_request():
            nonlocal successful_requests, failed_requests
            
            async with semaphore:
                try:
                    start_time = time.time()
                    
                    # Make request based on method
                    if method.upper() == "GET":
                        async with self.session.get(
                            f"{self.config.base_url}{endpoint}"
                        ) as response:
                            await response.text()
                            status = response.status
                    elif method.upper() == "POST":
                        async with self.session.post(
                            f"{self.config.base_url}{endpoint}",
                            json=payload
                        ) as response:
                            await response.text()
                            status = response.status
                    elif method.upper() == "PUT":
                        async with self.session.put(
                            f"{self.config.base_url}{endpoint}",
                            json=payload
                        ) as response:
                            await response.text()
                            status = response.status
                    else:
                        raise ValueError(f"Unsupported method: {method}")
                    
                    end_time = time.time()
                    response_time = (end_time - start_time) * 1000  # Convert to ms
                    
                    response_times.append(response_time)
                    
                    if 200 <= status < 300:
                        successful_requests += 1
                    else:
                        failed_requests += 1
                        errors.append(f"HTTP {status}")
                        
                except Exception as e:
                    failed_requests += 1
                    errors.append(str(e))
                    logger.error(f"Request failed: {e}")
        
        # Create tasks for concurrent requests
        tasks = []
        for user in range(self.config.concurrent_users):
            for request in range(requests_per_user):
                task = asyncio.create_task(make_request())
                tasks.append(task)
                
                # Stagger request start times during ramp-up
                if self.config.ramp_up_time > 0:
                    delay = (self.config.ramp_up_time / self.config.concurrent_users) * user
                    await asyncio.sleep(delay / self.config.concurrent_users)
        
        # Wait for all requests to complete
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Calculate statistics
        total_requests = successful_requests + failed_requests
        avg_response_time = statistics.mean(response_times) if response_times else 0
        min_response_time = min(response_times) if response_times else 0
        max_response_time = max(response_times) if response_times else 0
        
        # Calculate percentiles
        if response_times:
            sorted_times = sorted(response_times)
            p95_index = int(len(sorted_times) * 0.95)
            p99_index = int(len(sorted_times) * 0.99)
            p95_response_time = sorted_times[p95_index]
            p99_response_time = sorted_times[p99_index]
        else:
            p95_response_time = 0
            p99_response_time = 0
        
        # Calculate requests per second
        requests_per_second = total_requests / self.config.test_duration if self.config.test_duration > 0 else 0
        error_rate = (failed_requests / total_requests * 100) if total_requests > 0 else 0
        
        # Create result
        result = LoadTestResult(
            endpoint=endpoint,
            method=method,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            avg_response_time=avg_response_time,
            min_response_time=min_response_time,
            max_response_time=max_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            requests_per_second=requests_per_second,
            error_rate=error_rate,
            errors=list(set(errors)),  # Remove duplicates
            timestamp=datetime.utcnow()
        )
        
        self.results.append(result)
        
        logger.info(f"Endpoint {endpoint} completed:")
        logger.info(f"  Total requests: {total_requests}")
        logger.info(f"  Success rate: {((successful_requests / total_requests) * 100):.2f}%")
        logger.info(f"  Avg response time: {avg_response_time:.2f}ms")
        logger.info(f"  P95 response time: {p95_response_time:.2f}ms")
        logger.info(f"  Requests/sec: {requests_per_second:.2f}")
    
    def _calculate_overall_success_rate(self) -> float:
        """Calculate overall success rate across all endpoints"""
        if not self.results:
            return 0.0
        
        total_successful = sum(r.successful_requests for r in self.results)
        total_requests = sum(r.total_requests for r in self.results)
        
        return (total_successful / total_requests * 100) if total_requests > 0 else 0.0
    
    def _calculate_overall_avg_response_time(self) -> float:
        """Calculate overall average response time"""
        if not self.results:
            return 0.0
        
        weighted_times = []
        for result in self.results:
            weighted_times.extend([result.avg_response_time] * result.total_requests)
        
        return statistics.mean(weighted_times) if weighted_times else 0.0
    
    def _calculate_overall_requests_per_second(self) -> float:
        """Calculate overall requests per second"""
        if not self.results:
            return 0.0
        
        total_requests = sum(r.total_requests for r in self.results)
        return total_requests / self.config.test_duration if self.config.test_duration > 0 else 0.0

class BetaLoadTestSuite:
    """Comprehensive load testing suite for beta testing"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.auth_token = None
        
    def authenticate(self, username: str, password: str) -> Optional[str]:
        """Authenticate and get auth token"""
        # This would make a real authentication request
        # For now, return a dummy token
        self.auth_token = "dummy-token"
        return self.auth_token
    
    async def run_api_load_test(self, concurrent_users: int = 10, duration: int = 60) -> LoadTestSummary:
        """Run API load test"""
        config = LoadTestConfig(
            base_url=self.base_url,
            concurrent_users=concurrent_users,
            test_duration=duration,
            ramp_up_time=10,
            endpoints=[
                {"endpoint": "/health", "method": "GET"},
                {"endpoint": "/auth/me", "method": "GET"},
                {"endpoint": "/portfolio", "method": "GET"},
                {"endpoint": "/analytics/performance", "method": "GET"},
                {"endpoint": "/market_data/quote/AAPL", "method": "GET"},
                {"endpoint": "/unified_accounts/summary", "method": "GET"},
            ],
            headers={"Authorization": f"Bearer {self.auth_token}"} if self.auth_token else None
        )
        
        runner = LoadTestRunner(config)
        return await runner.run_load_test("API Load Test")
    
    async def run_trading_load_test(self, concurrent_users: int = 5, duration: int = 30) -> LoadTestSummary:
        """Run trading-specific load test"""
        config = LoadTestConfig(
            base_url=self.base_url,
            concurrent_users=concurrent_users,
            test_duration=duration,
            ramp_up_time=5,
            endpoints=[
                {"endpoint": "/orders", "method": "GET"},
                {"endpoint": "/orders/history", "method": "GET"},
                {
                    "endpoint": "/orders", 
                    "method": "POST",
                    "payload": {
                        "symbol": "AAPL",
                        "quantity": 1,
                        "order_type": "market",
                        "side": "buy"
                    }
                },
            ],
            headers={"Authorization": f"Bearer {self.auth_token}"} if self.auth_token else None
        )
        
        runner = LoadTestRunner(config)
        return await runner.run_load_test("Trading Load Test")
    
    async def run_websocket_load_test(self, concurrent_connections: int = 20, duration: int = 60) -> Dict[str, Any]:
        """Run WebSocket load test"""
        logger.info(f"Starting WebSocket load test: {concurrent_connections} connections, {duration}s")
        
        successful_connections = 0
        failed_connections = 0
        messages_sent = 0
        messages_received = 0
        connection_times = []
        
        async def websocket_client():
            nonlocal successful_connections, failed_connections, messages_sent, messages_received
            
            try:
                import websockets
                
                start_time = time.time()
                
                # Connect to WebSocket
                uri = f"ws://localhost:8000/ws/portfolio?token={self.auth_token}"
                
                async with websockets.connect(uri) as websocket:
                    connection_time = (time.time() - start_time) * 1000
                    connection_times.append(connection_time)
                    successful_connections += 1
                    
                    # Send periodic messages
                    end_time = time.time() + duration
                    while time.time() < end_time:
                        try:
                            # Send heartbeat
                            await websocket.send(json.dumps({"type": "heartbeat"}))
                            messages_sent += 1
                            
                            # Wait for response
                            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                            messages_received += 1
                            
                            # Wait before next message
                            await asyncio.sleep(random.uniform(1, 3))
                            
                        except asyncio.TimeoutError:
                            logger.warning("WebSocket timeout")
                            break
                            
            except Exception as e:
                failed_connections += 1
                logger.error(f"WebSocket connection failed: {e}")
        
        # Create concurrent WebSocket connections
        tasks = [websocket_client() for _ in range(concurrent_connections)]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Calculate statistics
        total_connections = successful_connections + failed_connections
        success_rate = (successful_connections / total_connections * 100) if total_connections > 0 else 0
        avg_connection_time = statistics.mean(connection_times) if connection_times else 0
        
        return {
            "test_name": "WebSocket Load Test",
            "concurrent_connections": concurrent_connections,
            "duration": duration,
            "successful_connections": successful_connections,
            "failed_connections": failed_connections,
            "success_rate": success_rate,
            "avg_connection_time": avg_connection_time,
            "messages_sent": messages_sent,
            "messages_received": messages_received,
            "message_success_rate": (messages_received / messages_sent * 100) if messages_sent > 0 else 0,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def run_comprehensive_load_test(self) -> Dict[str, Any]:
        """Run comprehensive load test suite"""
        logger.info("Starting comprehensive load test suite")
        
        results = {
            "test_suite": "Comprehensive Load Test",
            "timestamp": datetime.utcnow().isoformat(),
            "results": {}
        }
        
        try:
            # Run API load test
            logger.info("Running API load test...")
            api_result = await self.run_api_load_test(concurrent_users=10, duration=30)
            results["results"]["api_load_test"] = asdict(api_result)
            
            # Run trading load test
            logger.info("Running trading load test...")
            trading_result = await self.run_trading_load_test(concurrent_users=5, duration=20)
            results["results"]["trading_load_test"] = asdict(trading_result)
            
            # Run WebSocket load test
            logger.info("Running WebSocket load test...")
            ws_result = await self.run_websocket_load_test(concurrent_connections=15, duration=30)
            results["results"]["websocket_load_test"] = ws_result
            
            # Calculate overall summary
            results["summary"] = {
                "total_tests": 3,
                "api_success_rate": api_result.overall_success_rate,
                "trading_success_rate": trading_result.overall_success_rate,
                "websocket_success_rate": ws_result["success_rate"],
                "overall_health": "good" if all([
                    api_result.overall_success_rate > 95,
                    trading_result.overall_success_rate > 95,
                    ws_result["success_rate"] > 90
                ]) else "needs_attention"
            }
            
        except Exception as e:
            logger.error(f"Load test suite failed: {e}")
            results["error"] = str(e)
        
        return results
    
    def save_results(self, results: Dict[str, Any], filename: Optional[str] = None):
        """Save load test results to file"""
        if not filename:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"load_test_results_{timestamp}.json"
        
        output_path = Path("load_test_results") / filename
        output_path.parent.mkdir(exist_ok=True)
        
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Load test results saved to {output_path}")
        return output_path

# Pre-configured load test scenarios
async def run_beta_load_tests():
    """Run beta load testing scenarios"""
    suite = BetaLoadTestSuite()
    
    # Authenticate (in real scenario, would use real credentials)
    suite.authenticate("test_user", "test_password")
    
    # Run comprehensive tests
    results = await suite.run_comprehensive_load_test()
    
    # Save results
    output_file = suite.save_results(results)
    
    return results, output_file

if __name__ == "__main__":
    # Run load tests
    asyncio.run(run_beta_load_tests())