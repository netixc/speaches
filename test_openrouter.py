#!/usr/bin/env python3
"""
Test script to verify OpenRouter configuration with Speaches.
This script tests the connection to OpenRouter and verifies the model works.
"""
import asyncio
import logging
import sys

from openai import AsyncOpenAI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_openrouter_connection() -> bool:
    """Test connection to OpenRouter API."""
    base_url = "https://openrouter.ai/api/v1"
    api_key = "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"
    model = "google/gemini-2.5-flash-lite-preview-09-2025"

    logger.info(f"Testing OpenRouter connection to {base_url}")
    logger.info(f"Using model: {model}")

    client = AsyncOpenAI(base_url=base_url, api_key=api_key, max_retries=0)

    try:
        logger.info("Sending test request...")
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Say 'Hello from OpenRouter!' in exactly 5 words."}],
            max_tokens=50,
        )

        logger.info("SUCCESS! Response received:")
        logger.info(f"Model: {response.model}")
        logger.info(f"Content: {response.choices[0].message.content}")
        logger.info(f"Usage: {response.usage}")
        return True

    except Exception as e:
        logger.error(f"FAILED! Error testing OpenRouter connection: {e}")
        logger.exception("Full error details:")
        return False


async def test_streaming() -> bool:
    """Test streaming response from OpenRouter."""
    base_url = "https://openrouter.ai/api/v1"
    api_key = "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"
    model = "google/gemini-2.5-flash-lite-preview-09-2025"

    logger.info("\nTesting streaming response...")

    client = AsyncOpenAI(base_url=base_url, api_key=api_key, max_retries=0)

    try:
        stream = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Count from 1 to 5, one number per line."}],
            stream=True,
            max_tokens=100,
        )

        logger.info("Streaming response:")
        collected_content = ""
        async for chunk in stream:
            if len(chunk.choices) > 0 and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                collected_content += content
                print(content, end="", flush=True)

        print()  # newline
        logger.info(f"\nSUCCESS! Streaming test completed. Received {len(collected_content)} characters")
        return True

    except Exception as e:
        logger.error(f"FAILED! Error testing streaming: {e}")
        logger.exception("Full error details:")
        return False


async def main() -> None:
    """Run all tests."""
    logger.info("=" * 60)
    logger.info("OpenRouter Configuration Test")
    logger.info("=" * 60)

    test1 = await test_openrouter_connection()
    test2 = await test_streaming()

    logger.info("\n" + "=" * 60)
    if test1 and test2:
        logger.info("ALL TESTS PASSED! OpenRouter is configured correctly.")
        logger.info("You can now use Speaches with OpenRouter.")
        sys.exit(0)
    else:
        logger.error("SOME TESTS FAILED! Check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
