#!/bin/bash
# Download required models for Speaches Realtime API

echo "Downloading TTS model (Kokoro)..."
curl -X POST http://localhost:8000/v1/models/speaches-ai/Kokoro-82M-v1.0-ONNX

echo -e "\n\nDownloading STT model (Whisper)..."
curl -X POST http://localhost:8000/v1/models/Systran/faster-distil-whisper-small.en

echo -e "\n\nModels downloaded! Ready to use."
