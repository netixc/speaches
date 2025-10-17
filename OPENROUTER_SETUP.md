# OpenRouter Setup for Speaches

This guide shows how to configure Speaches to use OpenRouter for LLM capabilities.

## Configuration

Your OpenRouter configuration has been set up in `.env`:

```bash
CHAT_COMPLETION_BASE_URL=https://openrouter.ai/api/v1
CHAT_COMPLETION_API_KEY=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
LOG_LEVEL=info
```

## Model

The configured model is: `google/gemini-2.5-flash-lite-preview-09-2025`

This is Google's Gemini 2.5 Flash Lite model, which offers:
- Fast response times (good for real-time voice)
- Cost-effective pricing
- Strong reasoning capabilities

## Testing

### Test OpenRouter Connection

Run the test script to verify your configuration:

```bash
uv run python test_openrouter.py
```

This tests:
1. Basic API connectivity
2. Model availability
3. Streaming support

### Start Speaches Server

Start the server with your configuration:

```bash
# For CPU-only systems
docker compose up

# For CUDA-enabled systems
docker compose -f compose.cuda.yaml up

# In detached mode (background)
docker compose up -d
```

The server will be available at `http://localhost:8000`

## Using the Realtime API

### WebSocket Connection

Connect to the Realtime API with your OpenRouter model:

```javascript
const ws = new WebSocket(
  "ws://localhost:8000/v1/realtime?model=google/gemini-2.5-flash-lite-preview-09-2025"
);
```

### Transcription-Only Mode

For transcription without AI responses:

```javascript
const ws = new WebSocket(
  "ws://localhost:8000/v1/realtime?model=Systran/faster-distil-whisper-small.en&intent=transcription"
);
```

### Example Script

Run the example script to see it in action:

```bash
uv run python example_realtime_openrouter.py
```

## Architecture

```
User Audio Input
    ↓
Speaches Realtime API
    ↓
├─ STT: faster-whisper (local)
├─ TTS: Kokoro (local)
└─ LLM: OpenRouter → Gemini 2.5 Flash Lite (cloud)
    ↓
Audio/Text Output
```

## Available Models on OpenRouter

You can use any OpenRouter model by changing the `model` parameter. Popular options:

- `google/gemini-2.5-flash-lite-preview-09-2025` (fast, cost-effective)
- `google/gemini-2.5-flash-preview-09-2025` (better quality)
- `anthropic/claude-3.5-sonnet` (excellent reasoning)
- `openai/gpt-4-turbo` (OpenAI's flagship)
- `meta-llama/llama-3.1-70b-instruct` (open source)

Check https://openrouter.ai/models for full list and pricing.

## Session Configuration

Update session settings dynamically:

```javascript
ws.send(JSON.stringify({
  type: "session.update",
  session: {
    model: "google/gemini-2.5-flash-lite-preview-09-2025",
    instructions: "You are a helpful AI assistant.",
    voice: "af_heart",
    temperature: 0.7
  }
}));
```

## Troubleshooting

### Server won't start

Check that `.env` file exists and has correct configuration:
```bash
cat .env
```

### Connection errors

Verify OpenRouter API key is valid:
```bash
uv run python test_openrouter.py
```

### Model not found

Ensure the model name is correct and available on OpenRouter:
- Visit https://openrouter.ai/models
- Copy the exact model ID

### Performance issues

For real-time voice chat, you need:
- CUDA GPU for TTS/STT (CPU will be slow)
- Fast LLM with low TTFT (Gemini Flash is good)
- Good internet connection to OpenRouter

## Next Steps

1. Start the Speaches server: `docker compose up`
2. Test with example script: `uv run python example_realtime_openrouter.py`
3. Build your application using the Realtime API
4. Check documentation at https://speaches.ai/usage/realtime-api

## Security Notes

- Keep your OpenRouter API key secure
- Never commit `.env` to git (it's already in `.gitignore`)
- Monitor your OpenRouter usage and costs
- Consider adding Speaches API key for production (`API_KEY` in `.env`)
