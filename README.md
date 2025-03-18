# Nexus AI Assistant

Nexus is an advanced AI assistant with hybrid local/cloud capabilities, extensive plugin support, intelligent context handling, and Manus AI integration for enhanced capabilities.

## Key Features

- **Hybrid AI Processing**: Automatically switches between local GPT-Neo model and cloud API based on system load
- **Context-Aware Conversations**: Maintains conversation history with automatic summarization of older context
- **Intelligent Request Routing**: Uses advanced intent classification to route requests to appropriate services
- **Plugin System**: Expandable capabilities through a flexible plugin architecture
- **Advanced AI Capabilities**: Integrates with state-of-the-art models like Claude and GPT-4o via capability abstraction layer
- **Web Browsing & Scraping**: Browse websites, extract content, and take screenshots
- **Vector Storage & RAG**: Store and retrieve embeddings with Pinecone or ChromaDB for enhanced retrieval
- **Responsive UI**: Modern web interface with real-time monitoring and Google OAuth authentication

## Manus AI Integration

Nexus now integrates Manus AI capabilities through an extensible abstraction layer:

1. **Advanced Language Models**: Access to Claude, GPT-4o, and other cutting-edge AI models
2. **Capability Abstraction**: Unified interface for all AI services with automatic fallbacks
3. **Web Intelligence**: Automated browsing, content extraction, and web interaction
4. **Enhanced RAG**: Vector storage with Pinecone and ChromaDB for powerful information retrieval
5. **Multimodal Support**: Handling of text, code, web, and vector embeddings seamlessly

See [MANUS_AI_CAPABILITIES.md](MANUS_AI_CAPABILITIES.md) for detailed documentation and usage examples.

## System Advantages

Nexus AI provides several key advantages:

1. **Resource Optimization**: Dynamically balances between local processing (faster, private) and cloud APIs (more capable) based on system load and query complexity
2. **Memory Management**: Implements sliding context window with automatic summarization to maintain coherent conversations without running out of memory
3. **Hardware Utilization**: Specifically optimized for i7-13700K, RTX 3070Ti, and 32GB DDR5 hardware configuration
4. **Extensibility**: Plugin architecture and capability abstraction allow for easy integration of new AI services
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
│   ├── capability/       # Capability abstraction layer
│   │   └── providers/    # Capability providers (language, web, vector)
│   ├── language/         # Language processing services
│   ├── rag/              # Retrieval-Augmented Generation
│   ├── agents/           # Agent framework
│   └── system/           # System management
└── infrastructure/       # Infrastructure layer
    ├── performance/      # Performance monitoring and optimization
    └── security/         # Authentication and authorization
```

## Advanced AI Capabilities

Nexus offers multiple levels of AI capabilities:

1. **Base AI**
   - **Local Model**: Uses GPT-Neo-125M running locally on your GPU
     - Handles most common queries
     - Provides faster responses
     - Ensures privacy for sensitive information
     - No internet connection required
   - **Cloud Fallback**: Uses Hugging Face API when needed
     - Handles complex queries beyond local model capabilities
     - Activates automatically when system load exceeds thresholds
     - Manages throttling and API rate limits

2. **Enhanced AI (Manus Integration)**
   - **Premium Language Models**: Claude and GPT-4o access
     - Superior reasoning and instruction following
     - Specialized code generation capabilities
     - Advanced context handling
   - **Web Intelligence**: Automated web browsing
     - Content extraction and summarization
     - Screenshot capture
     - JavaScript execution
   - **Vector Storage**: Enhanced RAG capabilities
     - Pinecone integration for production deployments
     - ChromaDB for local vector storage
     - Semantic search and retrieval

3. **Intelligent Orchestration**
   - Selects appropriate capability for each request
   - Handles fallbacks gracefully
   - Provides unified experience across all AI services
   - Optimizes for cost, performance, and quality

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
   
   For Manus AI capabilities, add your API keys:
   ```
   # Language Model APIs
   ANTHROPIC_API_KEY=your_anthropic_api_key
   OPENAI_API_KEY=your_openai_api_key
   
   # Web Browsing APIs
   BROWSERLESS_API_KEY=your_browserless_api_key
   
   # Vector Storage APIs
   PINECONE_API_KEY=your_pinecone_api_key
   PINECONE_ENVIRONMENT=your_pinecone_environment
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
