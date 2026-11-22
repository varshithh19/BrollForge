# Comprehensive Test Report — BrollForge

This document records the automated testing execution, evidence locations, pass/fail status, and systematic outcomes for all 20 Hard Cases as required by IncuBrix PS3 Section 18 and Section 19.

---

## 1. Test Suite Summary

- **Test Framework:** Pytest 9.2 with `pytest-asyncio`
- **Execution Command:** `python scripts/run_tests.py`
- **Test Categories:** API & Security, Audio & Silence Detection, Meaning Segmentation & Metaphor Disambiguation, Footage Providers & Zero-Duplicate Licensing, End-to-End Multi-Ratio Video Rendering & Clip Swapping, 20 Hard Cases.
- **Total Test Cases:** 29 automated tests
- **Overall Result:** **ALL 29 TESTS PASSED (100% Pass Rate)**

---

## 2. Test Execution Details by Module

### A. API, Security & Idempotency (`backend/tests/test_api.py`)
| Test Name | Status | Verification Focus |
|---|---|---|
| `test_health_and_readiness` | **PASSED** | Verifies `/health` and `/ready` endpoints return HTTP 200 with DB and storage readiness. |
| `test_system_config_and_providers` | **PASSED** | Verifies `/api/v1/config` lists `en-IN-female` and `/api/v1/providers` lists active providers. |
| `test_job_submission_and_idempotency` | **PASSED** | Submits job with `Idempotency-Key`; retrying with same payload returns existing job; retrying with conflicting payload returns HTTP 409 `IDEMPOTENCY_KEY_MISMATCH`. |
| `test_ssrf_protection` | **PASSED** | Blocks attempts to access loopback `127.0.0.1` and cloud metadata `169.254.169.254` with `SSRF_SECURITY_VIOLATION`. |
| `test_job_query_endpoints` | **PASSED** | Tests pagination on `GET /api/v1/jobs` and verifies non-existent job returns HTTP 404 `JOB_NOT_FOUND`. |

### B. Audio Probing, Silence & Transcription (`backend/tests/test_audio_and_transcription.py`)
| Test Name | Status | Verification Focus |
|---|---|---|
| `test_audio_format_validation` | **PASSED** | Validates allowed extensions (`.mp3`, `.wav`, `.m4a`) and rejects invalid extensions (`.flac`, `.avi`). |
| `test_audio_probe_and_silence_detection` | **PASSED** | Probes sample audio for duration/rate; detects silent audio file (`hard_case_silent.wav`) and raises `SilentAudioError`. |
| `test_transcription_adapter` | **PASSED** | Transcribes audio segments, verifies start/end timestamps, words array, and detected language. |

### C. Meaning Segmentation & Metaphor Disambiguation (`backend/tests/test_segmentation_and_metaphor.py`)
| Test Name | Status | Verification Focus |
|---|---|---|
| `test_meaning_segmenter_gapless_coverage` | **PASSED** | Verifies 100% gapless coverage from `0.0s` to total audio duration with sentence/phrase boundaries. |
| `test_abstract_metaphors_and_disambiguation` | **PASSED** | Verifies metaphor translation for "trust is earned slowly" (handshake/partnership), "sales grew" (analytics), "cloud" (server data center), "bank" (finance office), "python" (software code). |

### D. Footage Providers, Licensing & Zero-Duplicate Rule (`backend/tests/test_footage_and_deduplication.py`)
| Test Name | Status | Verification Focus |
|---|---|---|
| `test_footage_fetcher_and_license_verification` | **PASSED** | Rejects non-commercial (`CC BY-NC`) candidates; verifies license URLs and commercial attribution. |
| `test_zero_duplicate_enforcement` | **PASSED** | Strict verification that a selected clip is NEVER reused in another scene within the same video. |
| `test_avoid_rules_enforcement` | **PASSED** | Verifies candidates violating avoid list constraints (e.g. alcohol, violence, faces) are disqualified. |

### E. End-to-End Multi-Ratio Rendering & Clip Swapping (`backend/tests/test_rendering_and_e2e.py`)
| Test Name | Status | Verification Focus |
|---|---|---|
| `test_end_to_end_video_generation_pipeline` | **PASSED** | Executes full pipeline producing 16:9 (`1920x1080`), 9:16 (`1080x1920`), and 1:1 (`1080x1080`) videos. Validates codec (`h264`), audio (`aac`), `30 fps`, `captions.srt`, `timeline.json`, `manifest.json`. Rerenders single scene via `ClipSwapper` in seconds. |

---

## 3. Systematic Verification of the 20 Hard Cases (`backend/tests/test_hard_cases.py`)

| Hard Case | Description | Input / Trigger | Expected Behavior | Actual Behavior | Result |
|---|---|---|---|---|---|
| **1** | Abstract narration | *"Trust is earned slowly."* | Meaningful visual metaphor (collaboration, partnership) | Search query translated to partnership/handshake | **PASS** |
| **2** | Statistics | *"Sales grew 40% in 2025."* | Corporate analytics / growth dashboard | Search query translated to financial analytics | **PASS** |
| **3** | Named real person | *"Sundar Pichai..."* | Respectful context without fabricating likeness | Avoid rules attach `people's faces` | **PASS** |
| **4** | Named brand | *"Google announced..."* | Product/engineering context without inventing logo | Avoid rules attach `logos` | **PASS** |
| **5** | Ambiguous: "value" | Enterprise value context | Abstract concept translated cleanly | Scene segmented with business value query | **PASS** |
| **6** | Ambiguous: "bank" | Commercial bank loan | Financial institution context, not riverbank | Query disambiguated to financial institution | **PASS** |
| **7** | Ambiguous: "cloud" | Cloud computing server | Data center server racks, not weather clouds | Disambiguated to data center server hardware | **PASS** |
| **8** | Ambiguous: "mouse" | Computer mouse hardware | Desktop workspace, not rodent | Disambiguated to computer mouse hardware | **PASS** |
| **9** | Ambiguous: "python" | Python automation code | Software developer coding, not snake reptile | Disambiguated to software programming terminal | **PASS** |
| **10** | Sensitive / sad news | Tragic event memorial | Serene, dignified landscape without sensationalism | Sensitivity marked `sensitive_respectful` | **PASS** |
| **11** | 9:16 aspect ratio | 16:9 source clip | Smart centered crop to 1080x1920 without stretching | Verified via FFprobe: 1080x1920, SAR=1, 30fps | **PASS** |
| **12** | Long voiceover (10m) | Duration probe | Validates <= 600s, rejects > 600s with clear message | Correct duration enforcement verified | **PASS** |
| **13** | Silent audio | Silent WAV file | Detects silence level < -50dB and raises error | Raises `SilentAudioError` with code `SILENT_AUDIO_DETECTED` | **PASS** |
| **14** | Music-only audio | Non-speech audio | Detects lack of speech and warns truthfully | Raises `MusicOnlyAudioError` (`SPEECH_NOT_DETECTED`) | **PASS** |
| **15** | Wrong file type | Unsupported `.flac` / `.avi` | Validates extensions and magic headers | Raises `ValidationError` with allowed formats list | **PASS** |
| **16** | Empty script | Whitespace only script | Validation failure HTTP 422 | Returns HTTP 422 `VALIDATION_ERROR` | **PASS** |
| **17** | Provider unavailable | Invalid or missing API key | Automatic failover to secondary / local pack | Seamless failover with recorded fallback in manifest | **PASS** |
| **18** | Provider returns 0 results | Obscure query | Automatic fallback to local verified licensed pack | Local pack selected; zero empty timeline gaps | **PASS** |
| **19** | Corrupted download | Invalid media file | Post-download ffprobe validation check | Corrupted clips rejected before scene composition | **PASS** |
| **20** | Simultaneous jobs | 2 concurrent user submissions | Safe job isolation, separate IDs and folders | Generated distinct job IDs with no shared file clash | **PASS** |

---

## 4. Evidence Locations
- **Rendered Videos:** `storage/jobs/<job_id>/brollforge_<job_id>_<ratio>.mp4`
- **Timeline Artifacts:** `storage/jobs/<job_id>/timeline.json`
- **Manifest Artifacts:** `storage/jobs/<job_id>/manifest.json`
- **Subtitles:** `storage/jobs/<job_id>/captions.srt`
- **Batch Runner Outputs:** `test_outputs/<job_id>/` and `test_outputs/batch_summary_report.json`
