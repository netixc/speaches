#!/usr/bin/env python3
"""
Example script showing how to use Speaches Realtime API with OpenRouter.

This demonstrates:
1. Connecting to the Speaches Realtime API WebSocket
2. Using OpenRouter's Gemini model for conversation
3. Transcription-only mode vs conversation mode

Before running:
1. Start Speaches server: docker compose up
2. Ensure .env file has OpenRouter configuration
"""
import asyncio
import json
import logging

import websockets

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

SPEACHES_URL = "ws://localhost:8000"
OPENROUTER_MODEL = "google/gemini-2.5-flash-lite-preview-09-2025"


async def example_transcription_only() -> None:
    """Example: Transcription-only mode (no LLM response)."""
    logger.info("=" * 60)
    logger.info("Example 1: Transcription-Only Mode")
    logger.info("=" * 60)

    url = f"{SPEACHES_URL}/v1/realtime?model=Systran/faster-distil-whisper-small.en&intent=transcription"

    async with websockets.connect(url) as websocket:
        logger.info("Connected to Speaches Realtime API (transcription-only mode)")

        async for message in websocket:
            event = json.loads(message)
            event_type = event.get("type")

            if event_type == "session.created":
                logger.info(f"Session created: {event['session']['id']}")
                logger.info("In transcription mode, audio will be transcribed but no AI response generated")

            elif event_type == "conversation.item.input_audio_transcription.completed":
                transcript = event.get("transcript", "")
                logger.info(f"Transcription: {transcript}")


async def example_conversation_mode() -> None:
    """Example: Full conversation mode with OpenRouter."""
    logger.info("=" * 60)
    logger.info("Example 2: Conversation Mode with OpenRouter")
    logger.info("=" * 60)

    url = f"{SPEACHES_URL}/v1/realtime?model={OPENROUTER_MODEL}"

    async with websockets.connect(url) as websocket:
        logger.info(f"Connected to Speaches Realtime API with model: {OPENROUTER_MODEL}")

        async def receive_events() -> None:
            """Receive and log events from the server."""
            async for message in websocket:
                event = json.loads(message)
                event_type = event.get("type")

                if event_type == "session.created":
                    logger.info(f"Session created: {event['session']['id']}")
                    logger.info(f"Conversation model: {event['session']['model']}")
                    logger.info(f"Speech model: {event['session']['speech_model']}")
                    logger.info(f"Voice: {event['session']['voice']}")

                elif event_type == "input_audio_buffer.speech_started":
                    logger.info("User started speaking")

                elif event_type == "input_audio_buffer.speech_stopped":
                    logger.info("User stopped speaking")

                elif event_type == "conversation.item.input_audio_transcription.completed":
                    transcript = event.get("transcript", "")
                    logger.info(f"User said: {transcript}")

                elif event_type == "response.created":
                    logger.info("AI response generation started")

                elif event_type == "response.audio_transcript.delta":
                    delta = event.get("delta", "")
                    print(delta, end="", flush=True)

                elif event_type == "response.audio_transcript.done":
                    transcript = event.get("transcript", "")
                    logger.info(f"\nAI response complete: {transcript}")

                elif event_type == "response.audio.delta":
                    logger.debug("Received audio data chunk")

                elif event_type == "response.done":
                    logger.info("Response generation complete")

                elif event_type == "error":
                    logger.error(f"Error: {event['error']}")

        await receive_events()


async def example_session_update() -> None:
    """Example: Update session configuration dynamically."""
    logger.info("=" * 60)
    logger.info("Example 3: Dynamic Session Configuration")
    logger.info("=" * 60)

    url = f"{SPEACHES_URL}/v1/realtime?model={OPENROUTER_MODEL}"

    async with websockets.connect(url) as websocket:
        logger.info("Connected to Speaches Realtime API")

        msg = await websocket.recv()
        event = json.loads(msg)
        if event.get("type") == "session.created":
            logger.info("Session created, updating configuration...")

            update_event = {
                "type": "session.update",
                "session": {
                    "instructions": "You are a helpful AI assistant. Keep responses concise and friendly.",
                    "voice": "af_heart",
                    "temperature": 0.7,
                    "modalities": ["text", "audio"],
                },
            }
            await websocket.send(json.dumps(update_event))
            logger.info("Sent session update")

            msg = await websocket.recv()
            event = json.loads(msg)
            if event.get("type") == "session.updated":
                logger.info("Session configuration updated successfully")
                logger.info(f"New instructions: {event['session']['instructions']}")


async def main() -> None:
    """Run examples."""
    logger.info("Speaches Realtime API Examples with OpenRouter")
    logger.info("Make sure Speaches server is running on localhost:8000")
    logger.info("")

    try:
        await example_session_update()
    except Exception as e:
        logger.error(f"Error: {e}")
        logger.info("\nMake sure:")
        logger.info("1. Speaches server is running (docker compose up)")
        logger.info("2. .env file has correct OpenRouter configuration")
        logger.info("3. OpenRouter API key is valid")


if __name__ == "__main__":
    asyncio.run(main())
