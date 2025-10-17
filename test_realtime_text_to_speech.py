#!/usr/bin/env python3
"""
Test Realtime API: Send text, get text + TTS audio response.
"""
import asyncio
import base64
import json
import logging
from pathlib import Path

import websockets

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

SPEACHES_URL = "ws://localhost:8000"
MODEL = "google/gemini-2.5-flash-lite-preview-09-2025"


async def test_text_to_speech() -> None:
    """Send text message and receive text + audio response."""
    url = f"{SPEACHES_URL}/v1/realtime?model={MODEL}"

    logger.info(f"Connecting to {url}")

    async with websockets.connect(url) as ws:
        logger.info("Connected!")

        # Wait for session.created
        msg = await ws.recv()
        event = json.loads(msg)
        if event["type"] == "session.created":
            logger.info(f"Session created: {event['session']['id']}")

        # Send a text message
        user_message = "Tell me a short joke about programming in one sentence."
        logger.info(f"\nSending message: {user_message}")

        # Create conversation item with text input
        await ws.send(json.dumps({
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": user_message
                    }
                ]
            }
        }))

        # Trigger response generation
        await ws.send(json.dumps({
            "type": "response.create"
        }))

        # Collect response
        text_response = ""
        audio_chunks = []

        logger.info("\nReceiving response...\n")

        async for msg in ws:
            event = json.loads(msg)
            event_type = event.get("type")

            if event_type == "response.text.delta":
                delta = event.get("delta", "")
                text_response += delta
                print(delta, end="", flush=True)

            elif event_type == "response.audio_transcript.delta":
                delta = event.get("delta", "")
                text_response += delta
                print(delta, end="", flush=True)

            elif event_type == "response.audio.delta":
                audio_data = event.get("delta", "")
                if audio_data:
                    audio_chunks.append(audio_data)
                    logger.debug(f"Received audio chunk ({len(audio_data)} chars base64)")

            elif event_type == "response.done":
                logger.info(f"\n\nResponse complete!")
                logger.info(f"Text: {text_response}")
                logger.info(f"Audio chunks received: {len(audio_chunks)}")

                if audio_chunks:
                    # Decode and save audio
                    audio_bytes = b"".join([base64.b64decode(chunk) for chunk in audio_chunks])
                    output_path = Path("response_audio.pcm")
                    output_path.write_bytes(audio_bytes)
                    logger.info(f"Audio saved to {output_path} ({len(audio_bytes)} bytes)")
                    logger.info("To play: ffplay -f s16le -ar 24000 -ac 1 response_audio.pcm")

                break

            elif event_type == "error":
                logger.error(f"Error: {event.get('error')}")
                break


async def main() -> None:
    """Run test."""
    try:
        await test_text_to_speech()
    except ConnectionRefusedError:
        logger.error("Cannot connect to Speaches server!")
        logger.error("Make sure server is running: docker compose up")
    except Exception as e:
        logger.exception(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
