#!/usr/bin/env python
"""
Test script for the Nexus MCP server.
This script tests the functionality of the MCP server and its integration with Nexus.
"""

import os
import sys
import json
import logging
import argparse
import asyncio
import time
from datetime import datetime
from typing import Dict, Any, List

# Add the parent directory to the Python path so we can import nexus_mcp
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

import httpx
from nexus_mcp.config import MCP_SERVER_URL, DATA_DIR, LOGS_DIR, REGISTRATION_FILE

# Configure logging
os.makedirs(LOGS_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOGS_DIR, 'mcp_test.log')),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("nexus_mcp_test")

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Nexus MCP Test Utility")
    
    parser.add_argument(
        "--server-url", 
        default=MCP_SERVER_URL,
        help=f"URL of the MCP server (default: {MCP_SERVER_URL})"
    )
    
    parser.add_argument(
        "--output-dir", 
        default=DATA_DIR,
        help=f"Directory to save test results (default: {DATA_DIR})"
    )
    
    parser.add_argument(
        "--tests",
        nargs="+",
        choices=["health", "resources", "tools", "integration", "performance", "all"],
        default=["all"],
        help="Tests to run (default: all)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    return parser.parse_args()

async def test_server_health(server_url: str) -> bool:
    """Test the health of the MCP server."""
    logger.info(f"Testing MCP server health at {server_url}")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{server_url}/health")
            
            if response.status_code == 200:
                health_data = response.json()
                logger.info(f"MCP server health check passed: {health_data['status']}")
                logger.info(f"Server: {health_data.get('server', 'unknown')}, Version: {health_data.get('version', 'unknown')}")
                logger.info(f"CPU: {health_data.get('cpu', 'unknown')}")
                logger.info(f"GPU: {health_data.get('gpu', 'unknown')}")
                return True
            else:
                logger.error(f"MCP server health check failed: {response.status_code} {response.text}")
                return False
    except Exception as e:
        logger.error(f"Error testing MCP server health: {str(e)}")
        return False

async def test_resource_access(server_url: str, output_dir: str) -> bool:
    """Test accessing resources from the MCP server."""
    logger.info("Testing MCP server resource access")
    
    resources_to_test = [
        "nexus://config",
        "nexus://config/features",
        "nexus://config/hardware"
    ]
    
    results = {}
    
    try:
        async with httpx.AsyncClient() as client:
            for resource in resources_to_test:
                logger.info(f"Testing resource: {resource}")
                
                try:
                    response = await client.post(
                        f"{server_url}/resources",
                        json={"resource_id": resource}
                    )
                    
                    if response.status_code == 200:
                        results[resource] = {
                            "status": "success",
                            "data": response.json()
                        }
                        logger.info(f"Resource {resource} access successful")
                    else:
                        results[resource] = {
                            "status": "error",
                            "error": f"{response.status_code} {response.text}"
                        }
                        logger.error(f"Resource {resource} access failed: {response.status_code} {response.text}")
                except Exception as e:
                    results[resource] = {
                        "status": "error",
                        "error": str(e)
                    }
                    logger.error(f"Error accessing resource {resource}: {str(e)}")
        
        # Save results to file
        output_file = os.path.join(output_dir, "resource_test_results.json")
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Resource test results saved to {output_file}")
        
        # Check if all resources were accessed successfully
        success = all(result["status"] == "success" for result in results.values())
        
        if success:
            logger.info("All resource tests passed")
        else:
            logger.error("Some resource tests failed")
        
        return success
    
    except Exception as e:
        logger.error(f"Error testing MCP server resources: {str(e)}")
        return False

async def test_tool_execution(server_url: str, output_dir: str) -> bool:
    """Test executing tools on the MCP server."""
    logger.info("Testing MCP server tool execution")
    
    tools_to_test = [
        {
            "tool_id": "process_data",
            "parameters": {
                "data": "This is a test text for processing. It contains multiple words and sentences. The MCP server should analyze this text."
            }
        },
        {
            "tool_id": "analyze_sentiment",
            "parameters": {
                "text": "I am very happy with the excellent performance of the Nexus MCP server implementation."
            }
        },
        {
            "tool_id": "generate_summary",
            "parameters": {
                "text": "The Model Context Protocol (MCP) is an open protocol that enables seamless integration between LLM applications and external data sources and tools. It provides a standardized way for AI assistants to access data and functionality. The Nexus project has implemented an MCP server to enhance its capabilities.",
                "max_length": 100
            }
        }
    ]
    
    results = {}
    
    try:
        async with httpx.AsyncClient() as client:
            for tool in tools_to_test:
                logger.info(f"Testing tool: {tool['tool_id']}")
                
                try:
                    response = await client.post(
                        f"{server_url}/tools",
                        json=tool
                    )
                    
                    if response.status_code == 200:
                        results[tool["tool_id"]] = {
                            "status": "success",
                            "data": response.json()
                        }
                        logger.info(f"Tool {tool['tool_id']} execution successful")
                    else:
                        results[tool["tool_id"]] = {
                            "status": "error",
                            "error": f"{response.status_code} {response.text}"
                        }
                        logger.error(f"Tool {tool['tool_id']} execution failed: {response.status_code} {response.text}")
                except Exception as e:
                    results[tool["tool_id"]] = {
                        "status": "error",
                        "error": str(e)
                    }
                    logger.error(f"Error executing tool {tool['tool_id']}: {str(e)}")
        
        # Save results to file
        output_file = os.path.join(output_dir, "tool_test_results.json")
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Tool test results saved to {output_file}")
        
        # Check if all tools were executed successfully
        success = all(result["status"] == "success" for result in results.values())
        
        if success:
            logger.info("All tool tests passed")
        else:
            logger.error("Some tool tests failed")
        
        return success
    
    except Exception as e:
        logger.error(f"Error testing MCP server tools: {str(e)}")
        return False

async def test_nexus_integration(output_dir: str) -> bool:
    """Test the integration between the MCP server and Nexus."""
    logger.info("Testing Nexus integration")
    
    try:
        # Check if the registration file exists
        if os.path.exists(REGISTRATION_FILE):
            with open(REGISTRATION_FILE, "r") as f:
                registration = json.load(f)
            
            logger.info(f"Found MCP registration: {registration.get('server_id', 'unknown')}")
            
            # Check registration data
            registration_valid = (
                'server_id' in registration and
                'server_url' in registration and
                'server_name' in registration and
                'capabilities' in registration and
                'status' in registration
            )
            
            if not registration_valid:
                logger.error("MCP registration file has invalid format")
                return False
            
            # Save integration test results
            output_file = os.path.join(output_dir, "integration_test_results.json")
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            integration_results = {
                "registration": registration,
                "status": "success" if registration_valid else "error",
                "timestamp": datetime.now().isoformat()
            }
            
            with open(output_file, "w") as f:
                json.dump(integration_results, f, indent=2)
            
            logger.info(f"Integration test results saved to {output_file}")
            
            return registration_valid
        else:
            logger.error("MCP registration file not found")
            return False
    
    except Exception as e:
        logger.error(f"Error testing Nexus integration: {str(e)}")
        return False

async def test_performance(server_url: str, output_dir: str) -> bool:
    """Test the performance of the MCP server."""
    logger.info("Testing MCP server performance")
    
    results = {
        "resources": {},
        "tools": {}
    }
    
    try:
        # Performance configuration
        iterations = 5
        max_response_time_ms = 1000
        
        # Test resource access performance
        resources_to_test = ["nexus://config", "nexus://config/hardware"]
        
        for resource_id in resources_to_test:
            logger.info(f"Testing performance of resource: {resource_id}")
            
            try:
                start_time = time.perf_counter()
                
                async with httpx.AsyncClient() as client:
                    for _ in range(iterations):
                        await client.post(
                            f"{server_url}/resources",
                            json={"resource_id": resource_id}
                        )
                
                end_time = time.perf_counter()
                
                avg_time_ms = (end_time - start_time) * 1000 / iterations
                within_limit = avg_time_ms <= max_response_time_ms
                
                results["resources"][resource_id] = {
                    "average_time_ms": avg_time_ms,
                    "iterations": iterations,
                    "within_limit": within_limit
                }
                
                logger.info(f"Resource {resource_id} performance: {avg_time_ms:.2f}ms (limit: {max_response_time_ms}ms)")
                
                if not within_limit:
                    logger.warning(f"Resource {resource_id} performance exceeds time limit")
            
            except Exception as e:
                results["resources"][resource_id] = {
                    "error": str(e)
                }
                logger.error(f"Error testing resource {resource_id} performance: {str(e)}")
        
        # Test tool execution performance
        tools_to_test = [
            {
                "tool_id": "process_data",
                "parameters": {
                    "data": "Performance test data"
                }
            },
            {
                "tool_id": "analyze_sentiment",
                "parameters": {
                    "text": "Performance test sentiment text"
                }
            }
        ]
        
        for tool in tools_to_test:
            tool_id = tool["tool_id"]
            logger.info(f"Testing performance of tool: {tool_id}")
            
            try:
                start_time = time.perf_counter()
                
                async with httpx.AsyncClient() as client:
                    for _ in range(iterations):
                        await client.post(
                            f"{server_url}/tools",
                            json=tool
                        )
                
                end_time = time.perf_counter()
                
                avg_time_ms = (end_time - start_time) * 1000 / iterations
                within_limit = avg_time_ms <= max_response_time_ms
                
                results["tools"][tool_id] = {
                    "average_time_ms": avg_time_ms,
                    "iterations": iterations,
                    "within_limit": within_limit
                }
                
                logger.info(f"Tool {tool_id} performance: {avg_time_ms:.2f}ms (limit: {max_response_time_ms}ms)")
                
                if not within_limit:
                    logger.warning(f"Tool {tool_id} performance exceeds time limit")
            
            except Exception as e:
                results["tools"][tool_id] = {
                    "error": str(e)
                }
                logger.error(f"Error testing tool {tool_id} performance: {str(e)}")
        
        # Save performance test results
        output_file = os.path.join(output_dir, "performance_test_results.json")
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Performance test results saved to {output_file}")
        
        # Check if all performance tests were successful
        resource_success = all(
            "error" not in result for result in results["resources"].values()
        )
        
        tool_success = all(
            "error" not in result for result in results["tools"].values()
        )
        
        success = resource_success and tool_success
        
        if success:
            logger.info("All performance tests completed")
        else:
            logger.error("Some performance tests failed")
        
        return success
    
    except Exception as e:
        logger.error(f"Error testing MCP server performance: {str(e)}")
        return False

async def run_tests(args) -> bool:
    """Run all specified tests."""
    logger.info("Starting MCP server tests")
    
    tests_to_run = args.tests
    if "all" in tests_to_run:
        tests_to_run = ["health", "resources", "tools", "integration", "performance"]
    
    results = {}
    
    # Test server health
    if "health" in tests_to_run:
        results["health"] = await test_server_health(args.server_url)
    
    # Test resource access
    if "resources" in tests_to_run:
        results["resources"] = await test_resource_access(args.server_url, args.output_dir)
    
    # Test tool execution
    if "tools" in tests_to_run:
        results["tools"] = await test_tool_execution(args.server_url, args.output_dir)
    
    # Test Nexus integration
    if "integration" in tests_to_run:
        results["integration"] = await test_nexus_integration(args.output_dir)
    
    # Test performance
    if "performance" in tests_to_run:
        results["performance"] = await test_performance(args.server_url, args.output_dir)
    
    # Calculate overall success
    overall_success = all(results.values())
    
    # Log results
    logger.info("Test results:")
    for test, result in results.items():
        logger.info(f"  {test}: {'PASS' if result else 'FAIL'}")
    
    logger.info(f"Overall test result: {'PASS' if overall_success else 'FAIL'}")
    
    # Save results to file
    output_file = os.path.join(args.output_dir, "test_results.json")
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, "w") as f:
        json.dump({
            "tests": {k: "PASS" if v else "FAIL" for k, v in results.items()},
            "overall": "PASS" if overall_success else "FAIL",
            "timestamp": datetime.now().isoformat()
        }, f, indent=2)
    
    logger.info(f"All test results saved to {output_file}")
    
    return overall_success

def main():
    """Main entry point for testing the MCP server."""
    args = parse_arguments()
    
    logger.info("Starting MCP server tests")
    logger.info(f"Server URL: {args.server_url}")
    logger.info(f"Output directory: {args.output_dir}")
    logger.info(f"Tests to run: {args.tests}")
    
    try:
        success = asyncio.run(run_tests(args))
        
        if success:
            logger.info("All tests passed")
            return 0
        else:
            logger.error("Some tests failed")
            return 1
    except KeyboardInterrupt:
        logger.info("Tests interrupted")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error in tests: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
