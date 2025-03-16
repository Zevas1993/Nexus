# Nexus AI Assistant

An intelligent AI assistant with modular architecture and advanced features.

## Overview

Nexus AI Assistant is a comprehensive, modular AI assistant platform that provides natural language processing, information retrieval, content creation, code assistance, and system management capabilities. It features an enhanced RAG (Retrieval-Augmented Generation) system, improved plugin architecture, comprehensive testing framework, and advanced monitoring and logging.

## Key Features

- **Modular Architecture**: Clean, layered architecture with clear separation of concerns
- **Enhanced RAG System**: Hybrid search with multi-vector retrieval and reranking
- **Improved Plugin System**: Dynamic loading with dependency management and hooks
- **Comprehensive Testing Framework**: Base test cases, fixtures, and report generation
- **Advanced Monitoring and Logging**: Prometheus metrics, health checks, and JSON logging
- **Containerization Support**: Docker and Docker Compose configuration
- **Comprehensive Documentation**: API, user, and developer documentation

## Getting Started

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/nexus-ai/nexus-assistant.git
   cd nexus-assistant
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the application:
   ```
   python run.py
   ```

### Docker Deployment

1. Build and start containers:
   ```
   docker-compose up -d
   ```

2. Access the application at:
   ```
   http://localhost:5000
   ```

## Documentation

- [API Documentation](docs/api_documentation.md)
- [User Documentation](docs/user_documentation.md)
- [Developer Guide](docs/developer_guide.md)

## Project Structure

```
nexus_improved/
├── docs/                      # Documentation
├── nexus/                     # Main package
│   ├── infrastructure/        # Infrastructure layer
│   ├── domain/                # Domain layer
│   ├── application/           # Application layer
│   ├── presentation/          # Presentation layer
│   └── features/              # Additional features
├── plugins/                   # Plugin directory
├── tests/                     # Test suite
├── requirements.txt           # Dependencies
├── setup.py                   # Package setup
├── Dockerfile                 # Docker configuration
└── docker-compose.yml         # Docker Compose configuration
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please see the [Developer Guide](docs/developer_guide.md) for more information on how to contribute to the project.
