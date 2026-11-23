
import subprocess
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from backend.app.config.settings import settings
from backend.app.core.errors import MusicOnlyAudioError
from backend.app.core.logging import logger


class TranscriptionAdapter(ABC):
    @abstractmethod
    def transcribe(self, audio_path: str) -> Dict[str, Any]:
        """
        Transcribes speech and returns segments with timestamps
        and word-level data.
        """
        pass


class FasterWhisperAdapter(TranscriptionAdapter):
    """
    Production transcription adapter using faster-whisper.

    Uses CPU-friendly settings to reduce memory pressure.
    No mock transcription fallback is permitted here.
    """

    def __init__(
        self,
        model_size: str = settings.WHISPER_MODEL,
        device: str = settings.WHISPER_DEVICE,
        compute_type: str = settings.WHISPER_COMPUTE_TYPE,
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type

        self.provider_name = "faster-whisper"
        self.version = "CTranslate2"
        self.license_info = "MIT License"

        self._model = None

    def _get_model(self):
        """Load the Whisper model lazily with limited CPU threads."""

        if self._model is None:
            try:
                from faster_whisper import WhisperModel

                logger.info(
                    f"Loading faster-whisper model '{self.model_size}' "
                    f"on {self.device} ({self.compute_type}) "
                    f"with cpu_threads=2 and num_workers=1"
                )

                self._model = WhisperModel(
                    self.model_size,
                    device=self.device,
                    compute_type=self.compute_type,
                    cpu_threads=2,
                    num_workers=1,
                )

            except Exception as e:
                logger.exception("Failed to load faster-whisper model")
                raise RuntimeError(
                    f"Could not load faster-whisper model: {e}"
                ) from e

        return self._model

    def _decode_audio(self, audio_path: str):
        """
        Decode audio using FFmpeg into mono 16 kHz float32 samples.
        Limit FFmpeg to one thread to reduce memory pressure.
        """

        import numpy as np

        cmd = [
            settings.FFMPEG_PATH,
            "-nostdin",
            "-threads",
            "1",
            "-i",
            str(audio_path),
            "-f",
            "s16le",
            "-ac",
            "1",
            "-acodec",
            "pcm_s16le",
            "-ar",
            "16000",
            "-",
        ]

        try:
            output = subprocess.check_output(
                cmd,
                stderr=subprocess.PIPE,
            )

            if not output:
                raise ValueError("FFmpeg produced empty audio output")

            audio_data = (
                np.frombuffer(output, np.int16)
                .astype(np.float32)
                / 32768.0
            )

            if audio_data.size == 0:
                raise ValueError("Decoded audio contains no samples")

            return audio_data

        except subprocess.CalledProcessError as e:
            error_message = (
                e.stderr.decode("utf-8", errors="replace")
                if e.stderr
                else str(e)
            )

            logger.error(f"Audio decoding failed: {error_message}")

            raise RuntimeError(
                f"Could not decode audio using FFmpeg: {error_message}"
            ) from e

    def transcribe(self, audio_path: str) -> Dict[str, Any]:
        """
        Perform real speech transcription using faster-whisper.

        Uses beam_size=1 and best_of=1 to reduce CPU and memory
        requirements. Errors are propagated instead of silently
        switching to mock transcription.
        """

        try:
            model = self._get_model()
            audio_data = self._decode_audio(audio_path)

            segments_gen, info = model.transcribe(
                audio_data,
                beam_size=1,
                best_of=1,
                word_timestamps=True,
                vad_filter=True,
                vad_parameters={
                    "min_silence_duration_ms": 500,
                },
                condition_on_previous_text=False,
            )

            segments_list = []
            full_text_parts = []
            total_words = 0

            for seg in segments_gen:
                clean_text = seg.text.strip()

                if not clean_text:
                    continue

                full_text_parts.append(clean_text)

                words_data = []

                if seg.words:
                    for word in seg.words:
                        word_text = word.word.strip()

                        if not word_text:
                            continue

                        words_data.append({
                            "word": word_text,
                            "start": round(word.start, 3),
                            "end": round(word.end, 3),
                            "probability": round(
                                word.probability, 3
                            ),
                        })

                        total_words += 1

                segments_list.append({
                    "id": seg.id,
                    "start": round(seg.start, 3),
                    "end": round(seg.end, 3),
                    "text": clean_text,
                    "no_speech_prob": getattr(
                        seg,
                        "no_speech_prob",
                        0.0,
                    ),
                    "words": words_data,
                })

            full_transcript = " ".join(full_text_parts)

            if not full_transcript or total_words == 0:
                raise MusicOnlyAudioError(
                    "No speech detected in the audio file. "
                    "The file may contain only music, silence, or noise."
                )

            result = {
                "text": full_transcript,
                "language": info.language,
                "language_probability": round(
                    info.language_probability, 3
                ),
                "duration": round(info.duration, 3),
                "segments": segments_list,
                "model_info": {
                    "provider": self.provider_name,
                    "model_name": self.model_size,
                    "version": self.version,
                    "license": self.license_info,
                },
            }

            logger.info(
                f"Transcription completed successfully. "
                f"Provider={self.provider_name}, "
                f"Words={total_words}, "
                f"Language={info.language}"
            )

            return result

        except MusicOnlyAudioError:
            raise

        except Exception as e:
            logger.exception(
                f"Faster-whisper transcription failed: {e}"
            )

            raise RuntimeError(
                "Speech transcription failed. "
                "Please check the audio, FFmpeg installation, "
                f"and Whisper configuration. Details: {e}"
            ) from e


class MockTranscriptionAdapter(TranscriptionAdapter):
    """
    Deterministic mock transcription adapter.

    Intended exclusively for automated testing.
    Never use this adapter for real production user requests.
    """

    def __init__(self, sample_text: Optional[str] = None):
        self.sample_text = sample_text or (
            "Trust is earned slowly. Sales grew 40% in 2025."
        )

        self.provider_name = "mock-whisper"
        self.version = "1.0.0"
        self.license_info = "MIT License"

    def transcribe(self, audio_path: str) -> Dict[str, Any]:
        sentences = [
            sentence.strip()
            for sentence in self.sample_text.split(".")
            if sentence.strip()
        ]

        segments = []
        current_time = 0.0
        duration_per_sentence = 3.5

        for idx, sentence in enumerate(sentences):
            start = current_time
            end = current_time + duration_per_sentence

            words = sentence.split()

            word_duration = (
                (end - start) / max(1, len(words))
            )

            word_objects = []

            for word_idx, word in enumerate(words):
                word_start = start + word_idx * word_duration
                word_end = word_start + word_duration

                word_objects.append({
                    "word": word,
                    "start": round(word_start, 3),
                    "end": round(word_end, 3),
                    "probability": 0.99,
                })

            segments.append({
                "id": idx,
                "start": round(start, 3),
                "end": round(end, 3),
                "text": sentence + ".",
                "no_speech_prob": 0.01,
                "words": word_objects,
            })

            current_time = end

        return {
            "text": self.sample_text,
            "language": "en",
            "language_probability": 0.99,
            "duration": round(current_time, 3),
            "segments": segments,
            "model_info": {
                "provider": self.provider_name,
                "model_name": "mock-base",
                "version": self.version,
                "license": self.license_info,
            },
        }


def get_transcription_adapter(
    mock: bool = False,
    sample_text: Optional[str] = None,
) -> TranscriptionAdapter:
    """
    Select the appropriate transcription adapter.

    Test environment:
        Uses mock transcription.

    Production/development environment:
        Uses real faster-whisper transcription.

    Initialization failures are raised instead of silently
    switching to mock transcription.
    """

    if mock or settings.APP_ENV == "test":
        logger.info("Using mock transcription adapter for testing")

        return MockTranscriptionAdapter(
            sample_text=sample_text
        )

    logger.info(
        "Using production faster-whisper transcription adapter"
    )

    return FasterWhisperAdapter()
