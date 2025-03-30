# Nexus MCP Server Implementation

This repository contains a complete implementation of a Model Context Protocol (MCP) server for the Nexus AI Assistant, optimized for Windows and the i7-13700k/RTX 3070ti/32GB DDR5 hardware configuration.

## Overview

The Nexus MCP Server provides a standardized way for Nexus AI Assistant to access resources and execute tools through the Model Context Protocol. This implementation includes:

- Cross-platform compatibility (Windows/Linux)
- Hardware-specific optimizations for i7-13700k CPU, RTX 3070ti GPU, and 32GB DDR5 RAM
- Type safety and validation using Pydantic
- Comprehensive error handling and logging
- Integration with Nexus AI Assistant
- Complete testing framework

## Directory Structure

```
nexus_mcp_project/
├── src/
│   ├── main.py                              # Main entry point
│   ├── nexus_mcp_connect.py                 # Nexus connection script
│   ├── nexus_mcp_test.py                    # Testing script
│   ├── nexus_mcp/
│   │   ├── __init__.py                      # Package initialization
│   │   ├── config.py                        # Configuration management
│   │   ├── hardware.py                      # Hardware detection and optimization
│   │   ├── server.py                        # MCP server initialization
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── base.py                      # Pydantic data models
│   │   ├── integration/
│   │   │   ├── __init__.py
│   │   │   └── nexus_integration.py         # Nexus integration
│   │   ├── resources/
│   │   │   ├── __init__.py
│   │   │   └── config.py                    # Resource implementations
│   │   └── tools/
│   │       ├── __init__.py
│   │       └── processing.py                # Tool implementations
├── logs/                                    # Log files
│   ├── mcp_server.log
│   ├── mcp_connect.log
│   └── mcp_test.log
├── data/                                    # Data files
│   ├── mcp_registration.json
│   └── test_results/
├── hardware_config.json                     # Hardware configuration
└── start_mcp_server.ps1                     # Startup script for Windows
```

## Installation

### Windows Installation

1. Run the installation script to set up the necessary directories and dependencies:

   ```powershell
   .\install_mcp_windows.ps1
   ```

2. Copy the files to the installation directory:

   ```powershell
   Copy-Item -Path 'C:\Users\Chris Boyd\Desktop\nexus_mcp' -Destination 'C:\Users\Chris Boyd\nexus_mcp_project\src' -Recurse
   Copy-Item -Path 'C:\Users\Chris Boyd\Desktop\main.py' -Destination 'C:\Users\Chris Boyd\nexus_mcp_project\src'
   Copy-Item -Path 'C:\Users\Chris Boyd\Desktop\nexus_mcp_connect.py' -Destination 'C:\Users\Chris Boyd\nexus_mcp_project\src'
   Copy-Item -Path 'C:\Users\Chris Boyd\Desktop\nexus_mcp_test.py' -Destination 'C:\Users\Chris Boyd\nexus_mcp_project\src'
   ```

### Manual Installation

1. Install required Python packages:
   
   ```
   pip install mcp pydantic fastapi uvicorn httpx psutil
   ```

2. Create the necessary directories:
   
   ```
   mkdir -p nexus_mcp_project/logs nexus_mcp_project/data nexus_mcp_project/src
   ```

3. Copy the source files to the appropriate locations.

## Usage

### Starting the Server

To start the MCP server:

```
cd nexus_mcp_project
.\start_mcp_server.ps1  # For Windows
```

Or manually:

```
cd nexus_mcp_project/src
python main.py
```

### Connecting to Nexus

To connect the MCP server to Nexus (if not already done by the startup script):

```
cd nexus_mcp_project/src
python nexus_mcp_connect.py
```

### Running Tests

To test the MCP server functionality:

```
cd nexus_mcp_project/src
python nexus_mcp_test.py
```

To run specific tests:

```
python nexus_mcp_test.py --tests health resources tools
```

Available test categories:
- `health`: Tests server health
- `resources`: Tests resource access
- `tools`: Tests tool execution
- `integration`: Tests Nexus integration
- `performance`: Tests server performance
- `all`: Runs all tests

## Features

### Resources

The MCP server provides the following resources:

- `nexus://config`: Nexus configuration data
- `nexus://config/features`: List of Nexus features
- `nexus://config/hardware`: Hardware configuration information

### Tools

The MCP server provides the following tools:

- `process_data`: Processes and analyzes text data
- `analyze_sentiment`: Analyzes sentiment of text
- `generate_summary`: Generates a summary of text

### Hardware Optimization

The MCP server automatically detects and optimizes for the following hardware:

- **CPU**: Intel i7-13700k (16 cores, 24 threads)
- **GPU**: Gigabyte RTX 3070ti
- **RAM**: 32GB DDR5

Optimizations include:
- Parallel processing with optimal worker count
- GPU acceleration when available
- Memory management optimized for 32GB RAM
- Batch size optimization

## Cross-Platform Compatibility

The MCP server is designed to work on both Windows and Linux systems. It automatically detects the platform and adjusts file paths and system calls accordingly.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
