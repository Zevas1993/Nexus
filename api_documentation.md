# Nexus AI Assistant API Documentation

## Overview

This document provides comprehensive documentation for the Nexus AI Assistant API. The API allows developers to interact with the Nexus AI system programmatically, enabling integration with other applications and services.

## Base URL

All API endpoints are relative to the base URL:

```
https://api.nexus-ai.example.com/v1
```

For local development, use:

```
http://localhost:5000/api/v1
```

## Authentication

Authentication is required for all API endpoints. Nexus AI Assistant uses JWT (JSON Web Tokens) for authentication.

### Google OAuth Authentication

```
POST /auth/google/callback
```

**Request Body:**
```json
{
  "id_token": "GOOGLE_ID_TOKEN"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Logged in successfully",
  "token": "JWT_TOKEN",
  "user": {
    "id": "user_id",
    "email": "user@example.com",
    "name": "User Name"
  }
}
```

### Authentication Headers

For all subsequent requests, include the JWT token in the Authorization header:

```
Authorization: Bearer JWT_TOKEN
```

## Core Endpoints

### Process Request

Process a natural language request with the Nexus AI Assistant.

```
POST /process
```

**Request Body:**
```json
{
  "request": "What is the capital of France?",
  "params": {
    "session_id": "optional_session_id",
    "use_rag": true,
    "use_plugins": true
  }
}
```

**Response:**
```json
{
  "status": "success",
  "response": "The capital of France is Paris.",
  "sources": [
    {
      "content": "Paris is the capital and most populous city of France.",
      "metadata": {
        "source": "Wikipedia",
        "url": "https://en.wikipedia.org/wiki/Paris"
      },
      "score": 0.95
    }
  ]
}
```

### System Status

Get system status information.

```
GET /status
```

**Response:**
```json
{
  "status": "success",
  "system_stats": {
    "cpu": {
      "percent": 25.5,
      "count": 8,
      "load": [1.2, 1.5, 1.8]
    },
    "memory": {
      "total": 16000000000,
      "available": 8000000000,
      "used": 8000000000,
      "percent": 50.0
    },
    "disk": {
      "total": 500000000000,
      "used": 250000000000,
      "free": 250000000000,
      "percent": 50.0
    }
  },
  "health": {
    "status": "healthy",
    "checks": {
      "cpu": {
        "status": "healthy",
        "message": "CPU usage is 25.5% (below 90% threshold)"
      },
      "memory": {
        "status": "healthy",
        "message": "Memory usage is 50.0% (below 90% threshold)"
      },
      "disk": {
        "status": "healthy",
        "message": "Disk usage is 50.0% (below 90% threshold)"
      }
    }
  }
}
```

### Monitor Stream

Get real-time event stream from the system.

```
GET /monitor
```

**Response:**
Server-Sent Events (SSE) stream with events in the format:

```
data: HH:MM:SS - Event message
```

## Session Management

### Get Session Titles

Get list of session titles for the current user.

```
GET /session_titles
```

**Response:**
```json
{
  "status": "success",
  "titles": ["Research Session", "Math Help", "Code Review"]
}
```

### Set Session Title

Set title for the current session.

```
POST /set_session_title
```

**Request Body:**
```json
{
  "title": "New Session Title"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Session title set to New Session Title"
}
```

### Create Session

Create a new session.

```
POST /session
```

**Request Body:**
```json
{
  "title": "New Session"
}
```

**Response:**
```json
{
  "status": "success",
  "session": {
    "id": "session_id",
    "title": "New Session",
    "created_at": "2025-03-16T20:00:00Z",
    "updated_at": "2025-03-16T20:00:00Z"
  }
}
```

### Get Session

Get session details.

```
GET /session/{session_id}
```

**Response:**
```json
{
  "status": "success",
  "session": {
    "id": "session_id",
    "title": "Session Title",
    "created_at": "2025-03-16T20:00:00Z",
    "updated_at": "2025-03-16T20:00:00Z",
    "messages": [
      {
        "role": "user",
        "content": "Hello",
        "timestamp": "2025-03-16T20:01:00Z"
      },
      {
        "role": "assistant",
        "content": "Hi there! How can I help you today?",
        "timestamp": "2025-03-16T20:01:01Z"
      }
    ]
  }
}
```

### Update Session

Update session details.

```
PUT /session/{session_id}
```

**Request Body:**
```json
{
  "title": "Updated Title",
  "messages": []  // Optional: Clear messages
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Session updated successfully"
}
```

### Delete Session

Delete a session.

```
DELETE /session/{session_id}
```

**Response:**
```json
{
  "status": "success",
  "message": "Session deleted successfully"
}
```

## Plugin Management

### Get Available Plugins

Get list of available plugins.

```
GET /plugins
```

**Response:**
```json
{
  "status": "success",
  "plugins": [
    {
      "name": "translation",
      "description": "Translate text to various languages",
      "default_prompt": "Translate 'Hello' to Spanish",
      "inputs": [
        {
          "id": "text",
          "type": "text",
          "label": "Text to translate",
          "default": "Hello"
        },
        {
          "id": "lang",
          "type": "select",
          "label": "Target language",
          "options": [
            { "value": "es", "label": "Spanish" },
            { "value": "fr", "label": "French" },
            { "value": "de", "label": "German" }
          ],
          "default": "es"
        }
      ]
    }
  ]
}
```

### Execute Plugin

Execute a specific plugin.

```
POST /plugin/{plugin_name}/execute
```

**Request Body:**
```json
{
  "inputs": {
    "text": "Hello",
    "lang": "es"
  }
}
```

**Response:**
```json
{
  "status": "success",
  "result": "Hola"
}
```

## Voice Integration

### Voice Recognition

Convert speech to text.

```
POST /voice/listen
```

**Response:**
```json
{
  "status": "success",
  "text": "Recognized speech text"
}
```

### Text-to-Speech

Convert text to speech.

```
POST /voice/speak
```

**Request Body:**
```json
{
  "text": "Text to be spoken"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Speaking..."
}
```

## Background Tasks

### Create Task

Create a long-running background task.

```
POST /task
```

**Request Body:**
```json
{
  "data": "Task input data"
}
```

**Response:**
```json
{
  "status": "success",
  "task_id": "task_id"
}
```

### Get Task Status

Get status of a background task.

```
GET /task_status/{task_id}
```

**Response:**
```json
{
  "status": "SUCCESS",  // PENDING, STARTED, SUCCESS, FAILURE
  "result": "Task result data"
}
```

## Error Handling

All API endpoints return appropriate HTTP status codes:

- 200: Success
- 400: Bad Request
- 401: Unauthorized
- 403: Forbidden
- 404: Not Found
- 500: Internal Server Error

Error responses have the following format:

```json
{
  "status": "error",
  "message": "Error message",
  "code": "ERROR_CODE"  // Optional
}
```

## Rate Limiting

API requests are limited to 10 requests per minute per user. When rate limit is exceeded, the API returns a 429 Too Many Requests status code.

## Versioning

The API version is included in the URL path (e.g., `/v1/process`). This ensures backward compatibility as the API evolves.

## Webhooks

Nexus AI Assistant supports webhooks for event notifications. Configure webhooks in the settings page of the web interface.

## SDK Libraries

Official SDK libraries are available for:

- Python: `pip install nexus-ai-client`
- JavaScript: `npm install nexus-ai-client`

## Examples

### Python Example

```python
import nexus_ai_client as nexus

# Initialize client
client = nexus.Client(api_key="YOUR_API_KEY")

# Process a request
response = client.process("What is the capital of France?")
print(response.text)  # "The capital of France is Paris."

# Use a plugin
translation = client.plugin("translation").execute(
    text="Hello",
    lang="es"
)
print(translation)  # "Hola"
```

### JavaScript Example

```javascript
import { NexusClient } from 'nexus-ai-client';

// Initialize client
const client = new NexusClient({ apiKey: 'YOUR_API_KEY' });

// Process a request
client.process("What is the capital of France?")
  .then(response => {
    console.log(response.text);  // "The capital of France is Paris."
  });

// Use a plugin
client.plugin("translation").execute({
  text: "Hello",
  lang: "es"
})
  .then(translation => {
    console.log(translation);  // "Hola"
  });
```

## Support

For API support, contact api-support@nexus-ai.example.com or visit the developer forum at https://developers.nexus-ai.example.com.
