"""
Developer guide for Nexus AI Assistant.

This document provides guidance for developers working with or extending the Nexus AI Assistant.
"""

# Nexus AI Assistant Developer Guide

## Introduction

This developer guide provides comprehensive information for developers who want to work with, extend, or contribute to the Nexus AI Assistant project. It covers the architecture, core components, development workflow, and best practices.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Core Components](#core-components)
3. [Development Environment Setup](#development-environment-setup)
4. [Project Structure](#project-structure)
5. [Development Workflow](#development-workflow)
6. [Testing](#testing)
7. [Plugin Development](#plugin-development)
8. [Contributing Guidelines](#contributing-guidelines)
9. [API Reference](#api-reference)
10. [Performance Considerations](#performance-considerations)

## Architecture Overview

Nexus AI Assistant follows a modular, layered architecture designed for extensibility, maintainability, and scalability:

### Architectural Layers

1. **Infrastructure Layer**: Provides foundational services like database access, caching, security, and logging.
2. **Domain Layer**: Contains core business logic and domain services.
3. **Application Layer**: Orchestrates domain services and implements application-specific use cases.
4. **Presentation Layer**: Handles user interaction through API endpoints and web interface.

### Key Design Patterns

- **Dependency Injection**: Services are injected through the ApplicationContext.
- **Repository Pattern**: Data access is abstracted through repositories.
- **Service Pattern**: Business logic is encapsulated in service classes.
- **Command Pattern**: Requests are processed as commands.
- **Observer Pattern**: Event-based communication between components.
- **Factory Pattern**: Creation of complex objects.

### Communication Flow

1. User request enters through the presentation layer
2. Request is routed to the appropriate controller
3. Controller delegates to application services
4. Application services coordinate domain services
5. Domain services perform business logic
6. Results flow back up through the layers
7. Response is formatted and returned to the user

## Core Components

### ApplicationContext

The central component that manages service instances and configuration. It provides:

- Service registration and retrieval
- Configuration management
- Dependency injection

```python
# Example usage
from nexus.infrastructure.context import ApplicationContext

# Create context with configuration
context = ApplicationContext(config)
context.initialize()

# Get a service
service = context.get_service(ServiceClass)
```

### Service Base Classes

All services extend from base service classes:

- `BaseService`: Synchronous service base class
- `AsyncService`: Asynchronous service base class

```python
from nexus.domain.base import AsyncService

class MyCustomService(AsyncService):
    async def _process_impl(self, request, **kwargs):
        # Implementation goes here
        return {"status": "success", "result": {...}}
```

### Orchestrator

Coordinates the processing of user requests by routing them to appropriate services:

```python
# Example orchestrator usage
orchestrator = create_orchestrator(app, app_context)
result = await orchestrator.process_request(
    "What is the capital of France?",
    user_email,
    session_title,
    {"use_rag": True}
)
```

### RAG System

The Retrieval-Augmented Generation system enhances responses with relevant context:

- `EmbeddingService`: Creates vector embeddings for text
- `IndexingService`: Manages document indices
- `RetrievalService`: Retrieves relevant documents
- `GenerationService`: Generates responses using retrieved context

### Plugin System

Enables extensibility through plugins:

- `PluginManifest`: Defines plugin metadata
- `PluginRegistry`: Manages plugin registration
- `PluginLoader`: Loads and initializes plugins
- `ImprovedPluginLoaderService`: Enhanced plugin loading with dependency management

## Development Environment Setup

### Prerequisites

- Python 3.10+
- Node.js 20+
- Redis
- PostgreSQL (optional, SQLite for development)
- Docker and Docker Compose (for containerized development)

### Setup Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/nexus-ai/nexus-assistant.git
   cd nexus-assistant
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. Initialize the database:
   ```bash
   python -m nexus.scripts.init_db
   ```

6. Run the development server:
   ```bash
   python run.py
   ```

### Docker Development

For containerized development:

```bash
# Build and start containers
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose -f docker-compose.dev.yml logs -f

# Stop containers
docker-compose -f docker-compose.dev.yml down
```

## Project Structure

```
nexus_improved/
├── docs/                      # Documentation
├── nexus/                     # Main package
│   ├── __init__.py            # Package initialization
│   ├── config.py              # Configuration management
│   ├── infrastructure/        # Infrastructure layer
│   │   ├── context.py         # Application context
│   │   ├── security/          # Security components
│   │   ├── database/          # Database access
│   │   ├── cache/             # Caching mechanisms
│   │   ├── logging/           # Logging utilities
│   │   └── storage/           # Storage utilities
│   ├── domain/                # Domain layer
│   │   ├── base.py            # Base service classes
│   │   ├── rag/               # RAG components
│   │   ├── voice/             # Voice services
│   │   ├── web/               # Web services
│   │   └── plugins/           # Plugin system
│   ├── application/           # Application layer
│   │   ├── orchestrator.py    # Request orchestration
│   │   ├── services/          # Application services
│   │   └── tasks/             # Background tasks
│   ├── presentation/          # Presentation layer
│   │   ├── api/               # API endpoints
│   │   └── web/               # Web interface
│   └── features/              # Additional features
│       ├── enhanced_rag.py    # Enhanced RAG system
│       ├── improved_plugins.py # Improved plugin system
│       ├── containerization.py # Containerization support
│       ├── testing.py         # Testing framework
│       └── monitoring.py      # Monitoring and logging
├── plugins/                   # Plugin directory
├── tests/                     # Test suite
├── requirements.txt           # Dependencies
├── run.py                     # Application entry point
└── docker-compose.yml         # Docker Compose configuration
```

## Development Workflow

### Feature Development

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/my-feature
   ```

2. **Implement the feature**:
   - Follow the architectural patterns
   - Add appropriate tests
   - Update documentation

3. **Run tests**:
   ```bash
   pytest
   ```

4. **Submit a pull request**:
   - Provide a clear description
   - Reference any related issues
   - Ensure CI checks pass

### Code Style

- Follow PEP 8 guidelines
- Use type hints
- Document classes and functions with docstrings
- Keep functions focused and small
- Use meaningful variable and function names

### Commit Guidelines

- Use conventional commits format:
  - `feat:` for new features
  - `fix:` for bug fixes
  - `docs:` for documentation changes
  - `test:` for test additions or changes
  - `refactor:` for code refactoring
  - `chore:` for maintenance tasks

## Testing

### Test Structure

- Unit tests: Test individual components in isolation
- Integration tests: Test component interactions
- End-to-end tests: Test complete workflows

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_specific_file.py

# Run tests with coverage
pytest --cov=nexus

# Generate coverage report
pytest --cov=nexus --cov-report=html
```

### Test Fixtures

Use the provided test fixtures for common test scenarios:

```python
def test_with_app_context(app_context):
    # Test using app_context fixture
    service = app_context.get_service(MyService)
    assert service is not None

def test_with_flask_app(flask_app, client):
    # Test using flask_app and client fixtures
    response = client.get('/')
    assert response.status_code == 200
```

## Plugin Development

### Plugin Structure

A plugin consists of:

1. A manifest file (`manifest.json`)
2. A main Python module
3. Optional additional modules and resources

### Creating a Plugin

1. Create a new directory in the `plugins` folder:
   ```bash
   mkdir -p plugins/my_plugin
   ```

2. Create a manifest file:
   ```json
   {
     "name": "my_plugin",
     "version": "1.0.0",
     "class_name": "MyPluginService",
     "dependencies": [],
     "description": "My custom plugin",
     "default_prompt": "Use my plugin to do something",
     "inputs": [
       {
         "id": "input1",
         "type": "text",
         "label": "Input 1",
         "default": "Default value"
       }
     ]
   }
   ```

3. Create the main plugin module:
   ```python
   # plugins/my_plugin/my_plugin.py
   from nexus.domain.base import AsyncService
   from nexus.features.improved_plugins import hook

   class MyPluginService(AsyncService):
       async def initialize(self):
           # Initialization code
           pass

       async def _process_impl(self, request, **kwargs):
           # Plugin implementation
           input1 = kwargs.get('input1', 'Default value')
           result = f"Processed {input1}"
           return {"status": "success", "result": result}

       @hook('before_response')
       async def before_response_hook(self, response):
           # Hook implementation
           return response
   ```

4. Test your plugin:
   ```bash
   python -m nexus.scripts.test_plugin my_plugin
   ```

### Plugin Hooks

Plugins can register hooks to interact with the system:

- `before_request`: Called before processing a request
- `after_request`: Called after processing a request
- `before_response`: Called before sending a response
- `on_error`: Called when an error occurs
- `on_startup`: Called when the system starts up
- `on_shutdown`: Called when the system shuts down

## Contributing Guidelines

### Contribution Process

1. Fork the repository
2. Create a feature branch
3. Implement your changes
4. Add tests
5. Update documentation
6. Submit a pull request

### Code Review

All pull requests undergo code review before merging:

- Code quality and style
- Test coverage
- Documentation
- Performance considerations
- Security implications

### Documentation

Update documentation for any changes:

- Code docstrings
- API documentation
- User documentation
- Developer guide

## API Reference

See the [API Documentation](api_documentation.md) for detailed information about the API endpoints.

## Performance Considerations

### Optimization Tips

- Use async/await for I/O-bound operations
- Use caching for expensive operations
- Optimize database queries
- Use connection pooling
- Implement pagination for large result sets
- Use background tasks for long-running operations

### Monitoring

Monitor performance using the built-in monitoring system:

- Request latency
- CPU and memory usage
- Database query performance
- Cache hit/miss ratio
- Model inference time

### Scaling

Strategies for scaling the application:

- Horizontal scaling with multiple instances
- Load balancing
- Database sharding
- Caching layer
- Message queues for asynchronous processing
- Containerization and orchestration with Kubernetes

## Conclusion

This developer guide provides a foundation for working with the Nexus AI Assistant. For more detailed information, refer to the specific documentation for each component and the API reference.

For questions or support, contact the development team at dev-support@nexus-ai.example.com or join our developer community at https://developers.nexus-ai.example.com/community.
