# Claude Code Web

A local web interface for Claude Code CLI that runs on your machine, providing a browser-based UI for interacting with Claude Code without relying on Claude Cloud.

## Features

- **Local Execution**: Runs entirely on your machine, interfacing with your local Claude Code CLI installation
- **Real-time Streaming**: WebSocket-based streaming for instant response display
- **Workspace Management**: Browse and select project directories
- **Conversation History**: Persistent conversation storage with session management
- **Modern UI**: Clean, responsive interface with dark/light themes
- **Docker Support**: Easy deployment with Docker and docker-compose

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Browser (Frontend)                        │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │   Chat UI    │  │  Workspace   │  │  Conversation        │  │
│  │              │  │  Browser     │  │  History             │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└───────────────────────────┬─────────────────────────────────────┘
                            │ WebSocket / REST API
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Backend Server                        │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  WebSocket   │  │   REST API   │  │  Session Manager     │  │
│  │  Manager     │  │   Endpoints  │  │                      │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└───────────────────────────┬─────────────────────────────────────┘
                            │ Subprocess
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Claude Code CLI                              │
│                (Installed on your machine)                       │
└─────────────────────────────────────────────────────────────────┘
```

## Prerequisites

1. **Python 3.11+**: Required for the backend server
2. **Claude Code CLI**: Must be installed and authenticated on your machine
   ```bash
   npm install -g @anthropic-ai/claude-code
   claude auth
   ```

## Quick Start

### Option 1: Run Directly

```bash
# Clone the repository
cd claude-code-web

# Run the start script
./run.sh

# Or manually:
pip install -r requirements.txt
cd backend
python main.py --host 127.0.0.1 --port 8080
```

Then open http://127.0.0.1:8080 in your browser.

### Option 2: Run with Docker

```bash
# Build and run with docker-compose
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## Configuration

Copy `config.yaml` to `config.local.yaml` and customize:

```yaml
server:
  host: "127.0.0.1"
  port: 8080
  reload: false

workspace:
  default: "~"
  favorites:
    - "~/projects"
    - "~/code"

claude:
  executable_path: ""  # Auto-detect
  timeout: 300
```

## Usage

### Basic Chat

1. Open the web interface at http://127.0.0.1:8080
2. Select or enter a workspace path (project directory)
3. Type your message and press Ctrl+Enter or click Send
4. Watch Claude Code respond in real-time

### Workspace Selection

- Click the folder icon to browse directories
- Double-click to navigate into directories
- Select a directory to use as your workspace

### Conversations

- Conversations are automatically saved
- Click on a conversation in the sidebar to resume
- Use the + button to start a new conversation

## API Endpoints

### REST API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/system` | GET | System information |
| `/api/workspaces` | GET | List available workspaces |
| `/api/conversations` | GET | List conversations |
| `/api/conversations` | POST | Create new conversation |
| `/api/conversations/{id}` | GET | Get conversation details |
| `/api/conversations/{id}` | DELETE | Delete conversation |
| `/api/chat` | POST | Send message (non-streaming) |

### WebSocket

Connect to `/ws/{client_id}` for real-time communication:

```javascript
// Send message
ws.send(JSON.stringify({
    action: "chat",
    message: "Explain this code",
    workspace: "/path/to/project",
    conversation_id: "optional-id"
}));

// Subscribe to conversation
ws.send(JSON.stringify({
    action: "subscribe",
    conversation_id: "conv-id"
}));

// Cancel request
ws.send(JSON.stringify({
    action: "cancel",
    conversation_id: "conv-id"
}));
```

## Project Structure

```
claude-code-web/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── claude_interface.py  # Claude Code CLI interface
│   ├── websocket_manager.py # WebSocket handling
│   └── models.py            # Pydantic models
├── frontend/
│   ├── index.html           # Main HTML page
│   └── static/
│       ├── styles.css       # Styles
│       └── app.js           # Frontend JavaScript
├── config.yaml              # Configuration file
├── requirements.txt         # Python dependencies
├── Dockerfile               # Docker build
├── docker-compose.yml       # Docker compose config
├── run.sh                   # Quick start script
└── README.md                # This file
```

## Security Considerations

- **Local Only**: By default, the server binds to `127.0.0.1` and is only accessible locally
- **No Authentication**: This is designed for local use; add authentication if exposing externally
- **File System Access**: The application can access files on your machine; be careful with workspace selection

## Troubleshooting

### Claude Code CLI not detected

1. Verify Claude Code is installed: `claude --version`
2. Ensure it's in your PATH or specify `executable_path` in config
3. Check authentication: `claude auth`

### WebSocket connection fails

1. Ensure no firewall blocking the port
2. Try a different port with `--port`
3. Check browser console for errors

### Permission errors

1. Ensure you have read access to the workspace directory
2. Check Docker volume mounts if using containers

## Development

```bash
# Run with auto-reload
./run.sh --reload

# Or with uvicorn directly
cd backend
uvicorn main:app --reload --host 127.0.0.1 --port 8080
```

## License

MIT License - See LICENSE file for details.
