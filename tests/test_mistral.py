"""
Simple script to test Mistral Small 3.1 integration.

This script tests the Mistral Small 3.1 model integration by sending a
simple request and displaying the response.

Usage:
    python -m tests.test_mistral
"""

import os
import sys
import asyncio
import json
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("test_mistral")

# Add project root to path to allow importing from nexus package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Load environment variables
load_dotenv()

async def test_mistral():
    """Test Mistral integration."""
    try:
        # Import Mistral model
        from nexus.models.mistral_model import MistralModel
        from nexus.core.config import model_config

        # Get API key from environment or config
        api_key = os.getenv("MISTRAL_SMALL_API_KEY", model_config.MISTRAL_SMALL_API_KEY)
        
        if not api_key:
            logger.error("Mistral API key not found. Please set MISTRAL_SMALL_API_KEY in your .env file.")
            return False
            
        logger.info("Testing Mistral Small 3.1 integration...")
        
        # Create model instance
        model = MistralModel()
        
        # Initialize the model
        await model.initialize()
        
        # Send test request
        test_prompt = "What are the three laws of robotics? Keep your answer concise."
        result = await model.process(test_prompt)
        
        # Display result
        logger.info("Successfully received response from Mistral Small 3.1:")
        print("\n" + "-" * 40)
        print("Test prompt: " + test_prompt)
        print("-" * 40)
        print(result.get("text", "No text in response"))
        print("-" * 40)
        print(f"Model: {result.get('model', 'unknown')}")
        print(f"Tokens: {result.get('total_tokens', 'unknown')}")
        print("-" * 40 + "\n")
        
        # Check if model info is available
        model_info = model.get_model_info()
        logger.info(f"Model information: {json.dumps(model_info, indent=2)}")
        
        return True
    except Exception as e:
        logger.error(f"Error testing Mistral: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    # Run the test
    success = asyncio.run(test_mistral())
    
    if success:
        logger.info("Mistral test completed successfully!")
        sys.exit(0)
    else:
        logger.error("Mistral test failed.")
        sys.exit(1)
