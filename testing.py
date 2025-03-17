"""
Testing framework for Nexus AI Assistant.

This module provides testing utilities, fixtures, and test runners.
"""

import os
import sys
import unittest
import pytest
import logging
import json
import asyncio
from typing import Dict, Any, List, Optional, Union, Callable
from pathlib import Path
from unittest.mock import MagicMock, patch
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class NexusTestCase(unittest.TestCase):
    """Base test case for Nexus AI Assistant."""
    
    def setUp(self):
        """Set up test case."""
        # Set up test environment
        os.environ["NEXUS_ENV"] = "test"
        os.environ["FLASK_ENV"] = "test"
        os.environ["DATABASE_URL"] = "sqlite:///:memory:"
        
        # Initialize test app context
        from nexus.config import Config
        self.config = Config()
        self.config.load_test_config()
        
        from nexus.infrastructure.context import ApplicationContext
        self.app_context = ApplicationContext(self.config)
        self.app_context.initialize()
        
    def tearDown(self):
        """Tear down test case."""
        # Clean up resources
        pass
    
    @contextmanager
    def mock_service(self, service_class, **kwargs):
        """Mock a service in the application context.
        
        Args:
            service_class: Service class to mock
            **kwargs: Attributes to set on the mock service
            
        Yields:
            Mock service instance
        """
        original_service = None
        mock_service = MagicMock(spec=service_class)
        
        # Set attributes on mock service
        for key, value in kwargs.items():
            setattr(mock_service, key, value)
        
        # Replace service in app context
        if service_class in self.app_context.services:
            original_service = self.app_context.services[service_class]
            self.app_context.services[service_class] = mock_service
        
        try:
            yield mock_service
        finally:
            # Restore original service
            if original_service is not None:
                self.app_context.services[service_class] = original_service

class AsyncNexusTestCase(NexusTestCase):
    """Base test case for asynchronous Nexus AI Assistant tests."""
    
    def setUp(self):
        """Set up test case."""
        super().setUp()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
    def tearDown(self):
        """Tear down test case."""
        self.loop.close()
        super().tearDown()
        
    def run_async(self, coro):
        """Run coroutine in event loop.
        
        Args:
            coro: Coroutine to run
            
        Returns:
            Coroutine result
        """
        return self.loop.run_until_complete(coro)

@pytest.fixture
def app_context():
    """Fixture for application context."""
    # Set up test environment
    os.environ["NEXUS_ENV"] = "test"
    os.environ["FLASK_ENV"] = "test"
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    
    # Initialize test app context
    from nexus.config import Config
    config = Config()
    config.load_test_config()
    
    from nexus.infrastructure.context import ApplicationContext
    app_context = ApplicationContext(config)
    app_context.initialize()
    
    yield app_context
    
    # Clean up resources
    pass

@pytest.fixture
def flask_app(app_context):
    """Fixture for Flask application."""
    from flask import Flask
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test_secret_key"
    
    # Configure app with app_context
    app.config.update(app_context.config)
    
    yield app

@pytest.fixture
def client(flask_app):
    """Fixture for Flask test client."""
    with flask_app.test_client() as client:
        yield client

class TestRunner:
    """Test runner for Nexus AI Assistant."""
    
    def __init__(self, test_dir: str = None):
        """Initialize test runner.
        
        Args:
            test_dir: Directory containing tests
        """
        self.test_dir = test_dir or "tests"
        
    def run_unittest(self, pattern: str = "test_*.py") -> unittest.TestResult:
        """Run unittest tests.
        
        Args:
            pattern: Test file pattern
            
        Returns:
            Test result
        """
        loader = unittest.TestLoader()
        suite = loader.discover(self.test_dir, pattern=pattern)
        runner = unittest.TextTestRunner(verbosity=2)
        return runner.run(suite)
    
    def run_pytest(self, args: List[str] = None) -> int:
        """Run pytest tests.
        
        Args:
            args: Pytest arguments
            
        Returns:
            Exit code
        """
        args = args or [self.test_dir]
        return pytest.main(args)
    
    def generate_test_report(self, result: unittest.TestResult, output_path: str = None) -> Dict[str, Any]:
        """Generate test report.
        
        Args:
            result: Test result
            output_path: Output path for report
            
        Returns:
            Test report
        """
        report = {
            "total": result.testsRun,
            "failures": len(result.failures),
            "errors": len(result.errors),
            "skipped": len(result.skipped),
            "success": result.wasSuccessful(),
            "details": {
                "failures": [
                    {
                        "test": str(test),
                        "message": message
                    }
                    for test, message in result.failures
                ],
                "errors": [
                    {
                        "test": str(test),
                        "message": message
                    }
                    for test, message in result.errors
                ],
                "skipped": [
                    {
                        "test": str(test),
                        "reason": reason
                    }
                    for test, reason in result.skipped
                ]
            }
        }
        
        if output_path:
            with open(output_path, "w") as f:
                json.dump(report, f, indent=2)
            
            logger.info(f"Test report generated at {output_path}")
        
        return report

def create_test_file(test_name: str, test_dir: str = "tests") -> str:
    """Create a test file.
    
    Args:
        test_name: Test name
        test_dir: Test directory
        
    Returns:
        Test file path
    """
    # Create test directory if it doesn't exist
    os.makedirs(test_dir, exist_ok=True)
    
    # Create test file
    test_file = os.path.join(test_dir, f"test_{test_name}.py")
    
    with open(test_file, "w") as f:
        f.write(f'''"""
Test {test_name} for Nexus AI Assistant.
"""

import unittest
import pytest
from nexus.testing import NexusTestCase, AsyncNexusTestCase

class Test{test_name.capitalize()}(NexusTestCase):
    """Test case for {test_name}."""
    
    def setUp(self):
        """Set up test case."""
        super().setUp()
        
    def test_{test_name}_basic(self):
        """Basic test for {test_name}."""
        # TODO: Implement test
        self.assertTrue(True)
        
    def test_{test_name}_advanced(self):
        """Advanced test for {test_name}."""
        # TODO: Implement test
        self.assertTrue(True)

class TestAsync{test_name.capitalize()}(AsyncNexusTestCase):
    """Async test case for {test_name}."""
    
    def setUp(self):
        """Set up test case."""
        super().setUp()
        
    def test_{test_name}_async(self):
        """Async test for {test_name}."""
        # TODO: Implement test
        async def async_test():
            return True
            
        result = self.run_async(async_test())
        self.assertTrue(result)

@pytest.mark.parametrize("input,expected", [
    ("test", "test"),
    ("example", "example")
])
def test_{test_name}_pytest(input, expected):
    """Pytest test for {test_name}."""
    assert input == expected
''')
    
    logger.info(f"Test file created at {test_file}")
    return test_file
