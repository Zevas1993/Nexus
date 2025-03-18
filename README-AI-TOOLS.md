# Nexus AI Coding Tools

This extension to the Nexus AI Assistant provides advanced AI-powered coding capabilities through a flexible plugin architecture, supporting multiple AI providers and tools.

## Features

- **Real-time Code Completion**: Get intelligent code suggestions as you type
- **Code Analysis**: Automatically detect bugs, security vulnerabilities, and code quality issues
- **Multi-provider Support**: Use multiple AI tools simultaneously with intelligent suggestion aggregation
- **Hybrid Processing**: Support for both local and cloud-based AI models
- **Resource Management**: Intelligent allocation and monitoring of system resources
- **Language Support**: Focused on Python and JavaScript, with extensibility for other languages

## Architecture

The AI Coding Tools extension is built on a modular plugin architecture:

```
nexus/
├── domain/
│   ├── ai_assistant/          # AI Assistant core
│   │   ├── base_plugin.py     # Base plugin interface
│   │   ├── plugin_registry.py # Plugin registration and role management
│   │   ├── orchestrator.py    # Coordinates multiple plugins
│   │   ├── aggregator.py      # Aggregates and deduplicates results
│   │   ├── resource_manager.py # System resource management
│   │   └── service.py         # Main service interface
├── plugins/
│   ├── tabnine_assistant/     # Code completion plugin
│   │   ├── manifest.json      # Plugin metadata
│   │   └── tabnine_assistant.py # Implementation
│   └── codiga_analyzer/       # Code analysis plugin
│       ├── manifest.json      # Plugin metadata
│       └── codiga_analyzer.py # Implementation
└── examples/                  # Example code and demo
    ├── code_sample.js         # JavaScript example
    ├── code_sample.py         # Python example
    └── ai_tools_demo.py       # Demo script
```

### Core Components

1. **Plugin System**: Base interfaces and registration mechanism for AI tools
2. **Orchestration**: Manages parallel execution of multiple AI plugins
3. **Result Aggregation**: Combines and ranks suggestions from multiple sources
4. **Resource Management**: Controls CPU, RAM, and GPU allocation

### Plugins

1. **Tabnine Assistant**: Code completion using Tabnine's AI models
   - Support for local and cloud processing
   - Language-aware suggestions
   - Multiple suggestion types (inline, snippet, function)

2. **Codiga Analyzer**: Code quality and security analysis
   - Vulnerability detection
   - Code quality assessment
   - Performance issue identification
   - Configurable analysis levels

## Installation & Configuration

### Requirements

- Python 3.8+
- Required packages (see requirements.txt)

### Dependencies

```
tabnine>=1.5.0      # Free API client for Tabnine
codiga-client>=0.1.2 # Code quality analysis
psutil>=5.9.0       # System resource monitoring
```

### Configuration

Both plugins have configurable options in their manifest.json files:

**Tabnine Assistant**:
- Processing mode (local/hybrid/cloud)
- Active languages
- Suggestion style

**Codiga Analyzer**:
- Analysis level (quick/standard/deep)
- Issue categories
- Rule sets

## Example Usage

### Code Completion

```python
from nexus.domain.ai_assistant import AIAssistantService

# Initialize service
app_context = AppContext()
service = AIAssistantService(app_context)
await service.initialize()

# Get code suggestions
code_context = {
    "code": "def calculate_average(numbers):\n    ",
    "language": "python",
    "line": 1,
    "column": 4,
    "filename": "example.py"
}

result = await service.get_code_suggestions(code_context)

# Process suggestions
if result["status"] == "success":
    for suggestion in result["suggestions"]:
        print(f"Suggestion: {suggestion['text']}")
        print(f"Confidence: {suggestion['confidence']}")
```

### Code Analysis

```python
from nexus.domain.ai_assistant import AIAssistantService

# Initialize service
app_context = AppContext()
service = AIAssistantService(app_context)
await service.initialize()

# Analyze code
code = """
def insecure_function(user_input):
    query = "SELECT * FROM users WHERE id = " + user_input
    return execute_query(query)
"""

result = await service.analyze_code(code, "example.py")

# Process analysis results
if result["status"] == "success":
    for location, issues in result["issues"].items():
        for issue in issues:
            print(f"Issue: {issue['name']}")
            print(f"Line {issue['line']}: {issue['message']}")
            print(f"Severity: {issue['severity']}")
```

## Demo

Run the included demo script to see the AI coding tools in action:

```bash
cd examples
python ai_tools_demo.py
```

The demo script showcases:
1. Code completion for Python and JavaScript
2. Code analysis for both languages
3. Resource usage monitoring

## Extensibility

The plugin architecture is designed for extensibility:

1. **Adding New Providers**: Create new plugin classes that implement the AIPlugin interface
2. **Adding New Languages**: Extend existing plugins with additional language support
3. **Custom Rules**: Add custom analysis rules for specific codebases or frameworks

## Future Enhancements

1. **UI Integration**: Rich code editor integration with inline suggestions and issue highlighting
2. **Learning System**: Adaptation to user preferences and coding style
3. **Additional Languages**: Support for TypeScript, Go, Rust, and more
4. **Documentation Generation**: AI-powered documentation creation and improvement
5. **Test Generation**: Automatic test case creation based on code

## License

This project is licensed under the MIT License - see the LICENSE file for details.
