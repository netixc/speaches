# Speaches

OpenAI API-compatible server for speech-to-text and text-to-speech with Realtime API support.

**Requires NVIDIA GPU with CUDA support**

## Quick Start

### Clone Repository

```bash
git clone https://github.com/netixc/speaches.git
cd speaches
```

### Setup Environment

Create a `.env` file in the project root:

```bash
# OpenRouter LLM Configuration
CHAT_COMPLETION_BASE_URL=https://openrouter.ai/api/v1
CHAT_COMPLETION_API_KEY=your-openrouter-api-key-here

# Optional: Set log level (debug, info, warning, error, critical)
LOG_LEVEL=info

# Optional: Speaches API key (uncomment if you want to secure your API)
# API_KEY=your-speaches-api-key-here
```

Get your OpenRouter API key from: https://openrouter.ai/keys

### Run Server

```bash
docker compose up

# In detached mode (background)
docker compose up -d
```

The server will be available at `http://localhost:8000`

## Realtime API Usage

Connect via WebSocket:

```javascript
const ws = new WebSocket(
  "ws://localhost:8000/v1/realtime?model=google/gemini-2.5-flash-lite-preview-09-2025"
);
```
