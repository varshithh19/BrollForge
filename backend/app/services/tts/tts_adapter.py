import asyncio
import os
import wave
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional
from backend.app.config.settings import settings
from backend.app.core.logging import logger

VOICE_MAP = {
    "en-IN-female": "en-IN-NeerjaNeural",
    "en-IN-male": "en-IN-PrabhatNeural",
    "en-US-female": "en-US-AriaNeural",
    "en-US-male": "en-US-GuyNeural",
    "en-GB-female": "en-GB-SoniaNeural",
    "hi-IN-female": "hi-IN-SwaraNeural",
    "hi-IN-male": "hi-IN-MadhurNeural",
    "ta-IN-female": "ta-IN-PallaviNeural",
}


class TTSAdapter(ABC):
    @abstractmethod
    async def generate_speech(self, text: str, output_path: str, voice: Optional[str] = None) -> Dict[str, Any]:
        """Synthesizes text to speech and outputs an audio file, returning synthesis metadata."""
        pass


class EdgeTTSAdapter(TTSAdapter):
    """
    Synthesizes speech using Microsoft Edge Neural TTS voices without external paid API keys.
    Commercially viable, high quality, and natively supports Indian English voices.
    """

    def __init__(self, default_voice: str = settings.DEFAULT_TTS_VOICE):
        self.default_voice = default_voice
        self.provider_name = "edge-tts"
        self.version = "6.1.12"
        self.license_info = "Microsoft Edge TTS public neural service interface"

    async def generate_speech(self, text: str, output_path: str, voice: Optional[str] = None) -> Dict[str, Any]:
        import edge_tts

        selected_voice = voice or self.default_voice
        # Resolve mapped voice identifier (e.g. en-IN-female -> en-IN-NeerjaNeural)
        target_voice = VOICE_MAP.get(selected_voice, selected_voice)

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        communicate = edge_tts.Communicate(text, target_voice)
        await communicate.save(output_path)

        logger.info(f"Generated TTS audio via {self.provider_name} with voice {target_voice} at {output_path}")

        return {
            "provider": self.provider_name,
            "version": self.version,
            "voice": target_voice,
            "requested_voice": selected_voice,
            "rate": "+0%",
            "volume": "+0%",
            "pitch": "+0Hz",
            "license": self.license_info,
        }


class MockTTSAdapter(TTSAdapter):
    """
    Mock TTS adapter for unit testing and offline environments.
    Generates a valid sine-wave / speech-simulating WAV file with precise duration.
    """

    def __init__(self, words_per_second: float = 2.5):
        self.words_per_second = words_per_second
        self.provider_name = "mock_tts"
        self.version = "1.0.0"

    async def generate_speech(self, text: str, output_path: str, voice: Optional[str] = None) -> Dict[str, Any]:
        import math
        import struct

        words = text.split()
        duration = max(1.5, len(words) / self.words_per_second)

        sample_rate = 16000
        total_samples = int(duration * sample_rate)

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with wave.open(output_path, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)

            # Generate gentle multi-tone audio mimicking vocal presence
            frames = bytearray()
            for i in range(total_samples):
                t = i / sample_rate
                # 220Hz + 440Hz formant simulation
                sample = int(3000 * math.sin(2 * math.pi * 220 * t) + 1500 * math.sin(2 * math.pi * 440 * t))
                frames.extend(struct.pack("<h", sample))
            wav_file.writeframes(frames)

        return {
            "provider": self.provider_name,
            "version": self.version,
            "voice": voice or "en-IN-female-mock",
            "rate": "1.0",
            "duration": duration,
            "license": "Internal Test Fixture (MIT)",
        }


def get_tts_adapter() -> TTSAdapter:
    if settings.TTS_PROVIDER == "mock" or settings.APP_ENV == "test":
        return MockTTSAdapter()
    return EdgeTTSAdapter()
