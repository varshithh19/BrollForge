from pathlib import Path
import pytest
from backend.app.core.errors import SilentAudioError, ValidationError
from backend.app.services.audio.probe import probe_audio, validate_audio_file
from backend.app.services.transcription.whisper_adapter import MockTranscriptionAdapter, get_transcription_adapter


def test_audio_format_validation():
    # Unsupported extension
    with pytest.raises(ValidationError) as exc:
        validate_audio_file("sample.flac")
    assert "Unsupported audio format" in str(exc.value)


def test_audio_probe_and_silence_detection():
    sample_wav = Path("./sample_inputs/sample_voiceover.wav")
    silent_wav = Path("./sample_inputs/hard_case_silent.wav")

    if sample_wav.exists():
        info = probe_audio(str(sample_wav))
        assert info["duration"] > 0
        assert info["sample_rate"] > 0
        assert info["is_silent"] is False

    if silent_wav.exists():
        with pytest.raises(SilentAudioError):
            probe_audio(str(silent_wav))


def test_transcription_adapter():
    mock_adapter = MockTranscriptionAdapter(sample_text="Trust is earned slowly. Sales grew 40% in 2025.")
    res = mock_adapter.transcribe("dummy_path.wav")
    assert "segments" in res
    assert len(res["segments"]) >= 2
    assert res["language"] == "en"
    for s in res["segments"]:
        assert s["end"] > s["start"]
        assert len(s["words"]) > 0
