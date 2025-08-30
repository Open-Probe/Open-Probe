# OpenProbe Backend API

FastAPI backend service for the **OpenProbe AI system**, specifically designed to integrate with and expose the powerful **DeepSearch module** for advanced AI reasoning and real-time search capabilities with WebSocket communication.

## Features

- 🚀 **FastAPI Framework**: High-performance async API
- 🧠 **DeepSearch Integration**: Seamlessly connects to the OpenProbe DeepSearch module for AI reasoning
- 🔄 **Real-time Updates**: WebSocket integration for live search progress and DeepSearch events
- 💾 **In-memory Sessions**: No database required, lightweight deployment
- 🔍 **OpenProbe Integration**: Direct connection to the AI reasoning system
- 📊 **Health Monitoring**: Built-in health checks and statistics
- 🛡️ **Error Handling**: Comprehensive error management and logging

## Quick Start

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set environment variables** (optional):
   ```bash
   # Copy your existing .env from the project root or set these
   WEB_SEARCH_API_KEY=your_key_here
   GOOGLE_API_KEY=your_key_here
   LAMBDA_API_KEY=your_key_here
   ```

3. **Run the server**:
   ```bash
   # From the backend directory
   python -m uvicorn app.main:app --reload --port 8000
   
   # Or run directly
   python app/main.py
   ```

4. **Access the API**:
   - API Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
   - Health Check: [http://localhost:8000/health](http://localhost:8000/health)
   - WebSocket: `ws://localhost:8000/ws`

## API Endpoints

### REST API

- `POST /api/v1/search` - Start a new search
- `GET /api/v1/search/{search_id}/status` - Get search status
- `POST /api/v1/search/{search_id}/cancel` - Cancel active search
- `POST /api/v1/new-chat` - Start new chat (clear session)
- `GET /health` - Health check
- `GET /stats` - Service statistics

### WebSocket

- `WS /ws` - Real-time communication for:
  - Step updates during search process
  - Search completion notifications
  - Error notifications
  - Session reset messages

## Architecture

### Core Services

- **SearchService**: Orchestrates search operations, utilizing the DeepSearch module
- **SessionManager**: Manages in-memory search sessions for DeepSearch queries
- **WebSocketManager**: Handles real-time client connections
- **DeepSearchAdapter**: Interfaces with the core OpenProbe DeepSearch AI reasoning system

### Data Flow

```
Client Request → SearchService → DeepSearchAdapter → OpenProbe DeepSearch AI Graph
                     ↓
WebSocket Updates ← WebSocketManager ← Session Updates
```

## Integration with OpenProbe DeepSearch

The backend integrates seamlessly with the existing OpenProbe DeepSearch system:

- **Graph Execution**: Uses the same `graph.ainvoke()` method from the DeepSearch module as `test_deepsearch.py`
- **State Management**: Maintains the same state structure for compatibility with DeepSearch operations
- **Real-time Streaming**: Converts DeepSearch graph events to WebSocket messages for the frontend
- **Error Handling**: Graceful degradation when the DeepSearch AI system is unavailable or encounters issues

## Configuration

Key configuration options in `app/config.py`:

- `MAX_CONCURRENT_SEARCHES`: Maximum simultaneous searches (default: 10)
- `SEARCH_TIMEOUT`: Search timeout in seconds (default: 300)
- `WS_HEARTBEAT_INTERVAL`: WebSocket heartbeat interval (default: 30)
- `MAX_REPLAN_ITER`: Maximum replanning iterations (default: 1)

## Development

### Project Structure
```
backend/
├── app/
│   ├── main.py              # FastAPI application
│   ├── config.py           # Configuration
│   ├── models/             # Pydantic models
│   ├── routes/             # API endpoints
│   ├── services/           # Business logic
│   └── utils/              # Utilities
├── requirements.txt        # Dependencies
└── README.md              # This file
```

### Running in Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run with auto-reload
uvicorn app.main:app --reload --port 8000

# Run with debug logging
LOG_LEVEL=DEBUG uvicorn app.main:app --reload --port 8000
```

### Testing

```bash
# Test health endpoint
curl http://localhost:8000/health

# Test search endpoint
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the capital of France?"}'

# Test WebSocket (using wscat)
npm install -g wscat
wscat -c ws://localhost:8000/ws
```

## Logging

The application uses structured logging with different levels:

- **INFO**: General application flow
- **DEBUG**: Detailed debugging information
- **WARNING**: Non-critical issues
- **ERROR**: Error conditions and exceptions

Log configuration can be modified in `app/config.py`.

## Error Handling

The API provides comprehensive error handling:

- **Validation Errors**: 422 for invalid request data
- **Search Errors**: 400 for search-related issues
- **Not Found**: 404 for missing resources
- **Server Errors**: 500 for internal errors

All errors include:
- Human-readable error message
- Error code for programmatic handling
- Timestamp
- Additional context when available

## Performance

### Optimization Features

- **Async/Await**: Full async support for non-blocking operations
- **Connection Pooling**: Efficient WebSocket connection management
- **Memory Management**: Automatic cleanup of expired sessions
- **Background Tasks**: Non-blocking search execution

### Monitoring

- Built-in health checks
- Session statistics
- Connection metrics
- Performance logging

## Troubleshooting

### Common Issues

1. **Import Error for DeepSearch modules**:
   - Ensure the backend is run from the project root and `src/deepsearch/` modules are correctly installed and accessible.
   - Check that `src/deepsearch/` modules are available
   - The system will run in mock mode if DeepSearch modules are unavailable

2. **WebSocket Connection Failed**:
   - Verify the server is running on the correct port
   - Check CORS configuration
   - Ensure firewall allows WebSocket connections

3. **Search Timeout**:
   - Increase `SEARCH_TIMEOUT` in configuration
   - Check DeepSearch system for performance issues
   - Monitor system resources

### Debug Mode

Enable debug logging for detailed troubleshooting:

```bash
LOG_LEVEL=DEBUG uvicorn app.main:app --reload
```

## Production Deployment

For production deployment:

1. Set `RELOAD=False` in configuration
2. Use a production WSGI server
3. Configure proper logging
4. Set up monitoring and health checks
5. Configure firewall and security settings
