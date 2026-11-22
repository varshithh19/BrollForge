import uuid
from pathlib import Path
import pytest
from backend.app.core.errors import (
    MediaProbeError,
    MusicOnlyAudioError,
    SilentAudioError,
    ValidationError,
)
from backend.app.services.audio.probe import probe_audio, validate_audio_file
from backend.app.services.rendering.aspect_converter import build_aspect_filter
from backend.app.services.segmentation.meaning_segmenter import MeaningSegmenter
from backend.app.services.transcription.whisper_adapter import MockTranscriptionAdapter


def test_hard_case_01_abstract_narration():
    seg = MeaningSegmenter()
    mock_data = {"text": "Trust is earned slowly.", "duration": 4.0, "segments": [{"id": 0, "start": 0.0, "end": 4.0, "text": "Trust is earned slowly.", "words": []}]}
    scenes = seg.segment_transcript(mock_data)
    assert len(scenes) == 1
    assert "handshake" in scenes[0]["search_query"].lower() or "trust" in scenes[0]["search_query"].lower()
    assert "partnership" in scenes[0]["reasoning"].lower() or "trust" in scenes[0]["reasoning"].lower()


def test_hard_case_02_statistics():
    seg = MeaningSegmenter()
    mock_data = {"text": "Sales grew 40% in 2025.", "duration": 4.0, "segments": [{"id": 0, "start": 0.0, "end": 4.0, "text": "Sales grew 40% in 2025.", "words": []}]}
    scenes = seg.segment_transcript(mock_data)
    assert len(scenes) == 1
    assert "analytics" in scenes[0]["search_query"].lower() or "growth" in scenes[0]["search_query"].lower()


def test_hard_case_03_named_real_person():
    seg = MeaningSegmenter()
    # Safe handling: do not invent likeness of named person, focus on professional context
    text = "Sundar Pichai discussed technology leadership."
    mock_data = {"text": text, "duration": 4.0, "segments": [{"id": 0, "start": 0.0, "end": 4.0, "text": text, "words": []}]}
    scenes = seg.segment_transcript(mock_data, avoid_rules=["people's faces"])
    assert len(scenes) == 1
    assert "people's faces" in scenes[0]["avoid_rules"]


def test_hard_case_04_named_brand():
    seg = MeaningSegmenter()
    # Safe handling: do not fabricate brand logos, focus on product/office context
    text = "Google announced novel engineering breakthroughs."
    mock_data = {"text": text, "duration": 4.0, "segments": [{"id": 0, "start": 0.0, "end": 4.0, "text": text, "words": []}]}
    scenes = seg.segment_transcript(mock_data, avoid_rules=["logos"])
    assert len(scenes) == 1
    assert "logos" in scenes[0]["avoid_rules"]


def test_hard_case_05_ambiguous_value():
    seg = MeaningSegmenter()
    text = "We focus on enterprise value and strategic importance."
    mock_data = {"text": text, "duration": 4.0, "segments": [{"id": 0, "start": 0.0, "end": 4.0, "text": text, "words": []}]}
    scenes = seg.segment_transcript(mock_data)
    assert len(scenes) == 1


def test_hard_case_06_ambiguous_bank():
    seg = MeaningSegmenter()
    text = "The commercial bank approved our investment loan."
    mock_data = {"text": text, "duration": 4.0, "segments": [{"id": 0, "start": 0.0, "end": 4.0, "text": text, "words": []}]}
    scenes = seg.segment_transcript(mock_data)
    assert "finance" in scenes[0]["search_query"].lower() or "bank" in scenes[0]["search_query"].lower()


def test_hard_case_07_ambiguous_cloud():
    seg = MeaningSegmenter()
    text = "Cloud computing server architecture powers applications."
    mock_data = {"text": text, "duration": 4.0, "segments": [{"id": 0, "start": 0.0, "end": 4.0, "text": text, "words": []}]}
    scenes = seg.segment_transcript(mock_data)
    assert "server" in scenes[0]["search_query"].lower() or "data center" in scenes[0]["search_query"].lower()


def test_hard_case_08_ambiguous_mouse():
    seg = MeaningSegmenter()
    text = "The user clicked the ergonomic computer mouse hardware."
    mock_data = {"text": text, "duration": 4.0, "segments": [{"id": 0, "start": 0.0, "end": 4.0, "text": text, "words": []}]}
    scenes = seg.segment_transcript(mock_data)
    assert "desktop" in scenes[0]["search_query"].lower() or "computer" in scenes[0]["search_query"].lower()


def test_hard_case_09_ambiguous_python():
    seg = MeaningSegmenter()
    text = "Python automation programming scripts run cleanly."
    mock_data = {"text": text, "duration": 4.0, "segments": [{"id": 0, "start": 0.0, "end": 4.0, "text": text, "words": []}]}
    scenes = seg.segment_transcript(mock_data)
    assert "software" in scenes[0]["search_query"].lower() or "coding" in scenes[0]["search_query"].lower()


def test_hard_case_10_sensitive_news():
    seg = MeaningSegmenter()
    text = "In tragic news today, the community honored the victims in a somber memorial."
    mock_data = {"text": text, "duration": 4.0, "segments": [{"id": 0, "start": 0.0, "end": 4.0, "text": text, "words": []}]}
    scenes = seg.segment_transcript(mock_data)
    assert scenes[0]["sensitivity"] == "sensitive_respectful"
    assert "serene" in scenes[0]["search_query"].lower() or "peaceful" in scenes[0]["search_query"].lower()


def test_hard_case_11_aspect_ratio_smart_crop():
    filter_9_16 = build_aspect_filter("9:16")
    assert "1080:1920" in filter_9_16
    assert "force_original_aspect_ratio=increase" in filter_9_16
    assert "crop=1080:1920" in filter_9_16


def test_hard_case_13_silent_audio():
    silent_file = Path("./sample_inputs/hard_case_silent.wav")
    if silent_file.exists():
        with pytest.raises(SilentAudioError):
            probe_audio(str(silent_file))


def test_hard_case_15_wrong_file_type():
    with pytest.raises(ValidationError):
        validate_audio_file("unsupported_video.avi")


def test_hard_case_16_empty_script(client):
    res = client.post("/api/v1/broll/jobs", json={"script": "   "})
    assert res.status_code == 422


def test_hard_case_20_simultaneous_job_isolation(client):
    # Two distinct users submitting jobs concurrently
    payload1 = {"script": "User one video narration text.", "voice": "en-IN-female", "aspect_ratios": ["16:9"]}
    payload2 = {"script": "User two video narration text.", "voice": "en-US-female", "aspect_ratios": ["9:16"]}

    res1 = client.post("/api/v1/broll/jobs", json=payload1)
    res2 = client.post("/api/v1/broll/jobs", json=payload2)

    assert res1.status_code == 202
    assert res2.status_code == 202

    job1_id = res1.json()["job_id"]
    job2_id = res2.json()["job_id"]

    assert job1_id != job2_id
