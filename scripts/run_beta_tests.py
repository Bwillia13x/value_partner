#!/usr/bin/env python3
"""Script to run comprehensive beta testing validation"""
import asyncio
import sys
import os
import logging
import json
from datetime import datetime
from pathlib import Path

# Add the services directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'services'))

from app.load_testing import BetaLoadTestSuite
from app.beta_testing import beta_testing_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('beta_testing.log')
    ]
)

logger = logging.getLogger(__name__)

class BetaTestValidator:
    """Comprehensive beta testing validation"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.load_test_suite = BetaLoadTestSuite(base_url)
        self.results = {}
        
    async def validate_system_health(self) -> Dict[str, Any]:
        """Validate basic system health"""
        logger.info("Validating system health...")
        
        import aiohttp
        
        health_checks = {
            "basic_health": "/health",
            "detailed_health": "/health/detailed",
            "monitoring_health": "/monitoring/health"
        }
        
        results = {}
        
        async with aiohttp.ClientSession() as session:
            for check_name, endpoint in health_checks.items():
                try:
                    async with session.get(f"{self.base_url}{endpoint}") as response:
                        status = response.status
                        data = await response.json()
                        
                        results[check_name] = {
                            "status": "healthy" if status == 200 else "unhealthy",
                            "status_code": status,
                            "response": data
                        }
                        
                        logger.info(f"Health check {check_name}: {status}")
                        
                except Exception as e:
                    results[check_name] = {
                        "status": "error",
                        "error": str(e)
                    }
                    logger.error(f"Health check {check_name} failed: {e}")
        
        return results
    
    async def validate_api_performance(self) -> Dict[str, Any]:
        """Validate API performance under load"""
        logger.info("Validating API performance...")
        
        # Authentication (would use real credentials in production)
        self.load_test_suite.authenticate("test_user", "test_password")
        
        # Run performance tests
        performance_tests = []
        
        # Light load test
        light_load = await self.load_test_suite.run_api_load_test(
            concurrent_users=5, 
            duration=30
        )
        performance_tests.append(("light_load", light_load))
        
        # Medium load test
        medium_load = await self.load_test_suite.run_api_load_test(
            concurrent_users=15, 
            duration=45
        )
        performance_tests.append(("medium_load", medium_load))
        
        # Heavy load test
        heavy_load = await self.load_test_suite.run_api_load_test(
            concurrent_users=25, 
            duration=60
        )
        performance_tests.append(("heavy_load", heavy_load))
        
        # Analyze results
        performance_results = {}
        for test_name, result in performance_tests:
            performance_results[test_name] = {
                "success_rate": result.overall_success_rate,
                "avg_response_time": result.overall_avg_response_time,
                "requests_per_second": result.overall_requests_per_second,
                "passed": result.overall_success_rate > 95 and result.overall_avg_response_time < 2000
            }
            
            logger.info(f"Performance test {test_name}:")
            logger.info(f"  Success rate: {result.overall_success_rate:.2f}%")
            logger.info(f"  Avg response time: {result.overall_avg_response_time:.2f}ms")
            logger.info(f"  Requests/sec: {result.overall_requests_per_second:.2f}")
        
        return performance_results
    
    async def validate_trading_functionality(self) -> Dict[str, Any]:
        """Validate trading functionality"""
        logger.info("Validating trading functionality...")
        
        trading_results = {}
        
        try:
            # Test trading API load
            trading_load = await self.load_test_suite.run_trading_load_test(
                concurrent_users=3,
                duration=30
            )
            
            trading_results["load_test"] = {
                "success_rate": trading_load.overall_success_rate,
                "avg_response_time": trading_load.overall_avg_response_time,
                "passed": trading_load.overall_success_rate > 98 and trading_load.overall_avg_response_time < 1000
            }
            
            # Test specific trading endpoints
            import aiohttp
            
            trading_endpoints = [
                "/orders",
                "/orders/history", 
                "/market_data/quote/AAPL",
                "/alpaca/account"
            ]
            
            endpoint_results = {}
            
            async with aiohttp.ClientSession() as session:
                for endpoint in trading_endpoints:
                    try:
                        start_time = time.time()
                        async with session.get(
                            f"{self.base_url}{endpoint}",
                            headers={"Authorization": f"Bearer {self.load_test_suite.auth_token}"}
                        ) as response:
                            response_time = (time.time() - start_time) * 1000
                            
                            endpoint_results[endpoint] = {
                                "status_code": response.status,
                                "response_time": response_time,
                                "passed": 200 <= response.status < 300 and response_time < 2000
                            }
                            
                    except Exception as e:
                        endpoint_results[endpoint] = {
                            "error": str(e),
                            "passed": False
                        }
            
            trading_results["endpoints"] = endpoint_results
            
        except Exception as e:
            trading_results["error"] = str(e)
            logger.error(f"Trading validation failed: {e}")
        
        return trading_results
    
    async def validate_real_time_capabilities(self) -> Dict[str, Any]:
        """Validate real-time WebSocket capabilities"""
        logger.info("Validating real-time capabilities...")
        
        try:
            # Test WebSocket load
            ws_results = await self.load_test_suite.run_websocket_load_test(
                concurrent_connections=10,
                duration=30
            )
            
            return {
                "websocket_load_test": ws_results,
                "passed": ws_results["success_rate"] > 90 and ws_results["message_success_rate"] > 95
            }
            
        except Exception as e:
            logger.error(f"Real-time validation failed: {e}")
            return {
                "error": str(e),
                "passed": False
            }
    
    async def validate_monitoring_and_metrics(self) -> Dict[str, Any]:
        """Validate monitoring and metrics collection"""
        logger.info("Validating monitoring and metrics...")
        
        import aiohttp
        
        monitoring_endpoints = [
            "/monitoring/metrics",
            "/monitoring/health",
            "/monitoring/stats",
            "/admin/performance"
        ]
        
        results = {}
        
        async with aiohttp.ClientSession() as session:
            for endpoint in monitoring_endpoints:
                try:
                    async with session.get(f"{self.base_url}{endpoint}") as response:
                        status = response.status
                        
                        if status == 200:
                            data = await response.json()
                            results[endpoint] = {
                                "status": "healthy",
                                "has_data": len(data) > 0,
                                "passed": True
                            }
                        else:
                            results[endpoint] = {
                                "status": "unhealthy",
                                "status_code": status,
                                "passed": False
                            }
                            
                except Exception as e:
                    results[endpoint] = {
                        "error": str(e),
                        "passed": False
                    }
        
        return results
    
    async def run_comprehensive_validation(self) -> Dict[str, Any]:
        """Run all beta testing validations"""
        logger.info("Starting comprehensive beta testing validation...")
        
        start_time = datetime.utcnow()
        
        validation_results = {
            "test_suite": "Beta Testing Validation",
            "start_time": start_time.isoformat(),
            "validations": {}
        }
        
        # Run all validations
        validations = [
            ("system_health", self.validate_system_health()),
            ("api_performance", self.validate_api_performance()),
            ("trading_functionality", self.validate_trading_functionality()),
            ("real_time_capabilities", self.validate_real_time_capabilities()),
            ("monitoring_metrics", self.validate_monitoring_and_metrics())
        ]
        
        for validation_name, validation_coro in validations:
            try:
                logger.info(f"Running {validation_name} validation...")
                result = await validation_coro
                validation_results["validations"][validation_name] = result
                
                # Log summary
                if isinstance(result, dict) and "passed" in result:
                    status = "PASSED" if result["passed"] else "FAILED"
                    logger.info(f"{validation_name}: {status}")
                
            except Exception as e:
                logger.error(f"Validation {validation_name} failed: {e}")
                validation_results["validations"][validation_name] = {
                    "error": str(e),
                    "passed": False
                }
        
        # Calculate overall results
        end_time = datetime.utcnow()
        validation_results["end_time"] = end_time.isoformat()
        validation_results["duration"] = (end_time - start_time).total_seconds()
        
        # Overall pass/fail
        all_passed = all(
            validation.get("passed", False) 
            for validation in validation_results["validations"].values()
            if isinstance(validation, dict)
        )
        
        validation_results["overall_result"] = "PASSED" if all_passed else "FAILED"
        
        logger.info(f"Beta testing validation completed: {validation_results['overall_result']}")
        logger.info(f"Total duration: {validation_results['duration']:.2f} seconds")
        
        return validation_results
    
    def save_results(self, results: Dict[str, Any], filename: Optional[str] = None):
        """Save validation results to file"""
        if not filename:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"beta_validation_results_{timestamp}.json"
        
        output_path = Path("beta_test_results") / filename
        output_path.parent.mkdir(exist_ok=True)
        
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Validation results saved to {output_path}")
        return output_path

async def main():
    """Main beta testing validation"""
    validator = BetaTestValidator()
    
    try:
        # Run comprehensive validation
        results = await validator.run_comprehensive_validation()
        
        # Save results
        output_file = validator.save_results(results)
        
        # Print summary
        print("\n" + "="*60)
        print("BETA TESTING VALIDATION SUMMARY")
        print("="*60)
        print(f"Overall Result: {results['overall_result']}")
        print(f"Duration: {results['duration']:.2f} seconds")
        print(f"Results saved to: {output_file}")
        
        # Print individual validation results
        for validation_name, validation_result in results["validations"].items():
            if isinstance(validation_result, dict):
                status = "PASSED" if validation_result.get("passed", False) else "FAILED"
                print(f"{validation_name.replace('_', ' ').title()}: {status}")
        
        print("="*60)
        
        # Exit with appropriate code
        exit_code = 0 if results["overall_result"] == "PASSED" else 1
        sys.exit(exit_code)
        
    except Exception as e:
        logger.error(f"Beta testing validation failed: {e}")
        print(f"\nERROR: Beta testing validation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    import time
    asyncio.run(main())