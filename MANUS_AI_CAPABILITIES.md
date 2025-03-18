# Manus AI Capabilities for Nexus

This document describes the Manus AI capabilities that have been integrated into Nexus, including configuration instructions and usage examples.

## Overview

Manus AI extends Nexus with a capability abstraction layer that seamlessly integrates multiple AI services:

1. **Advanced Language Models** - Interact with state-of-the-art language models like Claude and GPT-4o
2. **Web Browsing** - Browse websites, extract content, and take screenshots
3. **Vector Storage** - Store and retrieve vector embeddings for enhanced RAG capabilities
4. **Unified Interface** - Access all capabilities through a consistent API, with automatic fallbacks

## Configuration

### Environment Variables

You can configure the Manus AI capabilities via environment variables:

```bash
# Language Model APIs
export ANTHROPIC_API_KEY=your_anthropic_api_key
export OPENAI_API_KEY=your_openai_api_key

# Web Browsing APIs
export BROWSERLESS_API_KEY=your_browserless_api_key

# Vector Storage APIs
export PINECONE_API_KEY=your_pinecone_api_key
export PINECONE_ENVIRONMENT=your_pinecone_environment
```

### Configuration Object

Alternatively, you can pass a configuration object when initializing the `CapabilityService`:

```python
from nexus.domain.capability import CapabilityService

config = {
    "anthropic": {
        "api_key": "your_anthropic_api_key",
        "default_model": "claude-3-5-sonnet"
    },
    "openai": {
        "api_key": "your_openai_api_key",
        "default_model": "gpt-4o"
    },
    "browserless": {
        "api_key": "your_browserless_api_key"
    },
    "puppeteer": {
        "chrome_path": "/path/to/chrome" # Optional path to Chrome executable
    },
    "pinecone": {
        "api_key": "your_pinecone_api_key",
        "environment": "your_pinecone_environment",
        "index_name": "nexus-embeddings"
    },
    "chroma": {
        "host": "localhost",
        "port": 8000,
        "collection_name": "nexus-embeddings"
    },
    # Default provider settings
    "default_text_provider": "anthropic",
    "default_code_provider": "openai",
    "default_web_provider": "browserless",
    "default_vector_provider": "pinecone",
    # Enable/disable options
    "enable_local_puppeteer": True,
    "enable_chroma": True
}

capability_service = CapabilityService(config)
await capability_service.initialize()
```

## Usage Examples

### Text Generation

```python
response = await capability_service.generate_text(
    prompt="Explain quantum computing in simple terms",
    temperature=0.7,
    max_tokens=500
)

print(response["text"])

# Use a specific provider
response = await capability_service.generate_text(
    prompt="Explain quantum computing in simple terms",
    provider="openai",
    model="gpt-4-turbo"
)
```

### Code Generation

```python
code_response = await capability_service.generate_code(
    prompt="Create a function that calculates the Fibonacci sequence",
    language="python",
    temperature=0.2
)

print(code_response["code"])
```

### Web Browsing

```python
# Extract text content from a website
web_result = await capability_service.browse_url(
    url="https://www.example.com",
    extract_text=True
)

print(web_result["title"])
print(web_result["content"])

# Take a screenshot
screenshot_result = await capability_service.browse_url(
    url="https://www.example.com",
    take_screenshot=True,
    extract_text=False
)

# Save screenshot to file
with open("screenshot.jpg", "wb") as f:
    f.write(screenshot_result["screenshot"])

# Execute JavaScript on a website
script_result = await capability_service.browse_url(
    url="https://www.example.com",
    evaluate_script="return document.title + ' | ' + window.innerWidth + 'x' + window.innerHeight;"
)

print(script_result["script_result"])
```

### Vector Operations

```python
# Add vectors to Pinecone
vector_result = await capability_service.vector_operation(
    operation="upsert",
    vectors=[[0.1, 0.2, 0.3, ...], [0.4, 0.5, 0.6, ...]],  # 1536 dimensions for OpenAI embeddings
    ids=["doc1", "doc2"],
    metadata=[{"text": "Document 1"}, {"text": "Document 2"}]
)

# Query vectors
query_result = await capability_service.vector_operation(
    operation="query",
    query_vector=[0.1, 0.2, 0.3, ...],  # 1536 dimensions
    top_k=5
)

# Use ChromaDB instead of Pinecone
chroma_result = await capability_service.vector_operation(
    operation="add",
    vectors=[[0.1, 0.2, 0.3, ...], [0.4, 0.5, 0.6, ...]],
    ids=["doc1", "doc2"],
    metadata=[{"text": "Document 1"}, {"text": "Document 2"}],
    provider="chroma",
    documents=["Document 1 content", "Document 2 content"]  # Optional text content
)
```

## Integration with Nexus Orchestrator

The Manus AI capabilities are integrated with the Nexus orchestrator, which will automatically use the most appropriate capability for user requests.

## Requirements

- Python 3.9+
- aiohttp
- numpy
- For local browsing: pyppeteer
- For local vector storage: chromadb

## Optional APIs

While all capabilities can work with at least one free/local option, for optimal performance we recommend:

- Claude API key (anthropic.com)
- OpenAI API key (openai.com)
- Browserless API key (browserless.io)
- Pinecone API key (pinecone.io)

## Extending With New Providers

The capability abstraction layer can be extended with new providers. Each provider must:

1. Inherit from `CapabilityProvider`
2. Implement the required methods for capabilities
3. Be registered with the `CapabilityManager`

Example for implementing a new language model provider:

```python
from nexus.domain.capability.abstraction import CapabilityProvider, CapabilityType

class MyCustomLMProvider(CapabilityProvider):
    def __init__(self, config=None):
        super().__init__("my_custom_provider", config)
        
    async def initialize(self):
        # Initialize your provider
        self.register_capability(CapabilityType.TEXT_GENERATION, self.generate_text)
        
    async def generate_text(self, prompt, **kwargs):
        # Implement text generation
        return {
            "status": "success",
            "text": "Generated text"
        }

# Register the provider
capability_service.manager.register_provider(MyCustomLMProvider())
capability_service.manager.set_default_provider(CapabilityType.TEXT_GENERATION, "my_custom_provider")
