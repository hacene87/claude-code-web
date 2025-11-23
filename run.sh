#!/bin/bash
# Claude Code Web - Run Script
# Quick start script to run the web interface locally

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    Claude Code Web                             ║${NC}"
echo -e "${GREEN}║                 Local Web Interface                            ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is required but not installed.${NC}"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "Python version: ${GREEN}$PYTHON_VERSION${NC}"

# Check for Claude Code CLI
if command -v claude &> /dev/null; then
    CLAUDE_VERSION=$(claude --version 2>/dev/null || echo "unknown")
    echo -e "Claude Code CLI: ${GREEN}✓ $CLAUDE_VERSION${NC}"
else
    echo -e "Claude Code CLI: ${YELLOW}✗ Not found in PATH${NC}"
    echo -e "${YELLOW}Warning: Claude Code CLI should be installed for full functionality.${NC}"
    echo -e "${YELLOW}Install with: npm install -g @anthropic-ai/claude-code${NC}"
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo ""
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo ""
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install -q -r requirements.txt

# Parse arguments
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8080}"
RELOAD=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --host)
            HOST="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --reload)
            RELOAD="--reload"
            shift
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --host HOST    Host to bind to (default: 127.0.0.1)"
            echo "  --port PORT    Port to bind to (default: 8080)"
            echo "  --reload       Enable auto-reload for development"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Run the server
echo ""
echo -e "${GREEN}Starting server on http://${HOST}:${PORT}${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
echo ""

cd backend
python -m uvicorn main:app --host "$HOST" --port "$PORT" $RELOAD
