# Nexus AI Assistant

Nexus is an advanced AI assistant with hybrid local/cloud capabilities, extensive plugin support, and an intelligent context handling system.

## Key Features

- **Hybrid AI Processing**: Automatically switches between local GPT-Neo model and cloud API based on system load
- **Context-Aware Conversations**: Maintains conversation history with automatic summarization of older context
- **Intelligent Request Routing**: Uses advanced intent classification to route requests to appropriate services
- **Plugin System**: Expandable capabilities through a flexible plugin architecture
- **Responsive UI**: Modern web interface with real-time monitoring and Google OAuth authentication

## Advantages Over Manus AI

Nexus AI outperforms Manus AI in several key areas:

1. **Resource Optimization**: Dynamically balances between local processing (faster, private) and cloud APIs (more capable) based on system load and query complexity
2. **Memory Management**: Implements sliding context window with automatic summarization to maintain coherent conversations without running out of memory
3. **Hardware Utilization**: Specifically optimized for i7-13700K, RTX 3070Ti, and 32GB DDR5 hardware configuration
4. **Extensibility**: Plugin architecture allows for domain-specific capabilities like weather information without modifying core code
5. **Privacy**: Prioritizes local processing when possible, sending data to cloud only when necessary

## System Requirements

- **Processor**: i7-13700K or equivalent (recommended)
- **GPU**: NVIDIA RTX 3070Ti or equivalent (optional but recommended)
- **RAM**: 32GB DDR5 or equivalent
- **Storage**: 2GB minimum for core application, more for plugins and models
- **Operating System**: Windows 10/11, macOS, or Linux

## Architecture

Nexus uses a three-layer architecture for clean separation of concerns:

```
nexus/
├── application/          # Application layer
│   └── orchestrator.py   # Request orchestration
├── domain/               # Domain layer
│   ├── language/         # Language processing services
│   ├── rag/              # Retrieval-Augmented Generation
│   └── system/           # System management
└── infrastructure/       # Infrastructure layer
    ├── performance/      # Performance monitoring and optimization
    └── security/         # Authentication and authorization
```

## Hybrid AI Approach

The core innovation in Nexus is its hybrid AI system:

1. **Local Model**: Uses GPT-Neo-125M running locally on your GPU
   - Handles most common queries
   - Provides faster responses
   - Ensures privacy for sensitive information
   - No internet connection required

2. **Cloud Fallback**: Uses Hugging Face API when needed
   - Handles complex queries beyond local model capabilities
   - Activates automatically when system load exceeds thresholds
   - Provides higher quality responses for difficult questions
   - Manages throttling and API rate limits

3. **Intelligent Switching**: Seamlessly transitions between local and cloud
   - Monitors CPU and GPU utilization
   - Considers query complexity
   - Handles fallback gracefully when cloud is unavailable
   - Provides transparent operation to the user

## Getting Started

1. Clone the repository:
   ```bash
   git clone https://github.com/Zevas1993/Nexus.git
   cd Nexus
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create configuration:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

4. Run the application:
   ```bash
   python app.py
   ```

5. Open your browser to `http://localhost:5000`

## Docker Deployment

For containerized deployment:

```bash
docker-compose up -d
```

## Plugin Development

Create new plugins by adding a directory to the `plugins/` folder:

```
plugins/
└── my_plugin/
    ├── manifest.json    # Plugin metadata and UI configuration
    └── my_plugin.py     # Plugin implementation
```

See the weather plugin for an example implementation.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
