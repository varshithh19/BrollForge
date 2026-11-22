# PROJECT PLAN — BrollForge (IncuBrix Engineering Assessment 3)
## Script and Voiceover to B-roll Video Engine

### Executive Summary & Vision
BrollForge is an enterprise-grade, asynchronous video generation engine designed to transform raw voiceover audio or written scripts into license-clean, visually coherent, and precisely timed B-roll videos. Every scene is derived through meaning-based segmentation and voice-synchronized timing, backed by verifiable commercial-use stock footage and intelligent fallback mechanisms.

---

## 1. System Architecture

```
                  +----------------------------------------------+
                  |            Web Frontend (Vite/React)          |
                  | Dashboard | Create Video | Job Progress/View |
                  +----------------------+-----------------------+
                                         | HTTP / REST (Idempotent)
                                         v
                  +----------------------------------------------+
                  |         FastAPI REST Backend (v1 API)        |
                  |  - Auth/SSRF/URL Validation                 |
                  |  - Idempotency & Rate Limiting               |
                  |  - OpenAPI 3.1 & Structured JSON Logging     |
                  +----------------------+-----------------------+
                                         |
                     +-------------------+-------------------+
                     | Enqueue Job                           | Poll Status / Read
                     v                                       v
         +-----------------------+              +-----------------------+
         |     Redis Queue       |              |   PostgreSQL / SQLite |
         |   (RQ Worker Engine)  |              |    Job & Scene State  |
         +-----------+-----------+              +-----------------------+
                     | Worker Pops Job
                     v
         +-------------------------------------------------------+
         |                Core Pipeline Stages                   |
         |  1. Input Validation & Audio Ingestion / TTS (edge-tts)|
         |  2. Media Probe & Transcription (Whisper Adapter)    |
         |  3. Meaning-Based Scene Segmentation & Meta-Reasoning |
         |  4. Semantic Query Synthesis & Avoiding Constraints   |
         |  5. Dual Footage Search & Fallback Pipeline           |
         |     (Pexels API -> Wikimedia/Local Commercial -> Mock)|
         |  6. Semantic Ranking, Deduplication & Safety Checks  |
         |  7. Clip Acquisition, Checksum & Aspect Formatting   |
         |  8. FFmpeg Rendering: Normalization, Timing & Mix    |
         |  9. Dynamic Captions (SRT & Burn-in)                  |
         | 10. Multi-Ratio Composition (16:9, 9:16, 1:1)         |
         | 11. Artifact Output: timeline.json & manifest.json    |
         | 12. S3/MinIO & Local Storage Archival                 |
         +-------------------------------------------------------+
```

---

## 2. Modules and Responsibilities

| Module | Location | Primary Responsibilities |
| :--- | :--- | :--- |
| **API Layer** | `backend/app/api/v1/` | Job submission, idempotency handling, job status polling, scene swap endpoint, provider listing, system configuration. |
| **Audio & TTS** | `backend/app/services/audio/`, `tts/` | Audio inspection (ffprobe), format normalization (16kHz WAV), silence/music detection, TTS generation (`edge-tts` with `en-IN-female` and multi-voice support). |
| **Transcription** | `backend/app/services/transcription/` | Speech-to-text with segment and word-level timestamps (`faster-whisper` adapter with lightweight fallback for headless environments). |
| **Scene Segmentation** | `backend/app/services/segmentation/` | Meaning-based sentence/phrase boundary detection, concept extraction, concrete visual metaphor generation, avoid rule attachment, gapless timeline coverage. |
| **Footage Providers** | `backend/app/services/footage/` | Abstract provider interface, Pexels provider, Wikimedia/Pixabay secondary provider, local verified commercial footage pack provider, test mock provider. Verification of license URLs and commercial rights. |
| **Semantic Matching** | `backend/app/services/semantic_matching/` | Embedding-based semantic similarity scoring, subject relevance, avoidance penalty, strict deduplication across video scenes. |
| **Video Rendering** | `backend/app/services/rendering/` | FFmpeg pipelines for 16:9 (1920x1080), 9:16 (1080x1920), 1:1 (1080x1080), 30 fps, H.264/AAC, smart crop/pad, clip looping/trimming, narration audio overlay. |
| **Captions** | `backend/app/services/captions/` | SRT generation, subtitle alignment, FFmpeg subtitles filter styling for burned-in subtitles per aspect ratio. |
| **Validation & Manifests** | `backend/app/services/validation/`, `manifests/` | Black/frozen frame detection, audio drift verification, schema-compliant `timeline.json` and `manifest.json` generation. |
| **Worker Engine** | `backend/app/workers/` | Asynchronous task execution, stage-based progress updates (0-100%), error isolation, per-job temp workspaces, retry management. |
| **Frontend** | `frontend/` | React + TypeScript + Vite + Tailwind dashboard, interactive script/audio creation flow, live stage-progress monitor, video previewer, timeline/manifest inspector. |
| **CLI & Batch** | `scripts/batch_runner.py` | Headless execution, batch processing of script/audio folders, turnaround time measurement, test automation. |

---

## 3. Development Phases & Milestones

- **Phase 1: Foundation (Current)**
  - Workspace audit, environment setup, docker-compose configuration.
  - FastAPI application skeleton with health/readiness endpoints and structured JSON logger.
  - Database schema & migrations for jobs, scenes, and assets.
  - S3 / MinIO storage adapter with local filesystem fallback.

- **Phase 2: Input Processing & Meaning-Based Segmentation**
  - Audio ingestion, ffprobe validation (duration, format, silence check).
  - Configurable TTS engine supporting `en-IN-female` (`en-IN-NeerjaNeural`) and standard voices.
  - Whisper transcription adapter with timestamp preservation.
  - Sentence & phrase-level segmentation with visual metaphor synthesis.

- **Phase 3: Footage Sourcing, Semantic Matching & Licensing**
  - Footage provider abstraction layer.
  - Verified commercial license filters (Pexels, verified local licensed library, test mock).
  - Strict deduplication engine (provider ID, content hash, perceptual hash).
  - Avoid list and safety constraints (faces, alcohol, violence, brand likenesses).
  - Semantic ranking with normalized 1-5 scores and clear explanations.

- **Phase 4: FFmpeg Video Rendering & Captions**
  - Clip trimming, normalization (H.264, AAC, 30 fps, yuv420p).
  - Multi-aspect ratio engine: 16:9 (1920x1080), 9:16 (1080x1920), 1:1 (1080x1080).
  - Subtitle generation (`captions.srt`) and burned-in captions option.
  - Narration audio mix and drift check.
  - Generation of compliant `timeline.json` and `manifest.json`.

- **Phase 5: Integration Standard & API Completeness**
  - OpenAPI 3.1 specification (`openapi.yaml`).
  - Idempotency-Key support on POST endpoints.
  - Standardized error schema (`{"error": {"code": ..., "message": ..., ...}}`).
  - HMAC-SHA256 signed callbacks with `X-IncuBrix-Signature`.
  - Batch runner CLI script.

- **Phase 6: Advanced Features, Test Suite & Hard Cases**
  - Scene swap endpoint with partial segment rerender.
  - 20 Hard Case tests (abstract narration, statistics, named entities, silent audio, etc.).
  - Automated test suite covering unit, integration, and E2E pipelines.
  - Comprehensive documentation (`REPORT.md`, `SOURCES.md`, `AI_USE.md`, `TEST_REPORT.md`, `LICENSES.md`, `assessment_mapping.md`).

---

## 4. Assessment Requirement Traceability Matrix

| Requirement | Module | Verification Strategy |
| :--- | :--- | :--- |
| **1. Dual Input Modes (Audio & Script)** | `services/audio/`, `services/tts/` | Test MP3, WAV, M4A up to 10m; generate audio from script with `en-IN-female`. |
| **2. Meaning-Based Scenes & Timing** | `services/segmentation/` | Verify 100% audio coverage, sentence boundaries, semantic visual descriptions. |
| **3. License-Clean Footage** | `services/footage/` | Verify commercial licenses, attribution records, rejection of unverified clips. |
| **4. Consistent Video (16:9, 9:16, 1:1)**| `services/rendering/` | Check FFprobe outputs: H.264, AAC, 30fps, exact resolutions, no black/frozen frames. |
| **5. No Repeated Clips & Semantic Match**| `services/semantic_matching/` | Zero repeat-clip test; semantic scoring with 1-5 range and rationale. |
| **6. Safe Output & Sensitive Context** | `services/semantic_matching/` | Safety filters for real faces, brand logos, respectful metaphors for sensitive news. |
| **7. Resilient Background Jobs** | `workers/`, `services/footage/`| Asynchronous RQ worker, progressive stage reporting, automatic provider fallbacks. |
| **8. Ten Integration Standard Points** | `app/api/`, `docker-compose.yml` | Full OpenAPI 3.1, Idempotency-Key, structured logs, signed webhooks, batch runner. |
| **Advanced: Dual Source & Clip Swap** | `api/v1/jobs.py`, `services/rendering/`| Scene swap endpoint rerendering only target segment; multi-provider prioritization. |

---

## 5. Known Constraints and Mitigation Strategy

1. **Docker / FFmpeg Availability on Host:**
   - Docker Desktop may take time to initialize or may require WSL2 backend permissions on Windows.
   - *Mitigation:* We install FFmpeg locally via winget / static build AND build a containerized Docker Compose environment with FFmpeg 7+ inside Debian/Ubuntu containers. Local development and Docker modes are both fully supported with zero code modification.
2. **Third-Party API Keys (Pexels, etc.):**
   - External services require API keys that cannot be assumed in automated test environments.
   - *Mitigation:* Implement real HTTP adapters for Pexels and Pixabay/Wikimedia. Include verified local licensed stock footage (CC0 / Public Domain / Pexels licensed test assets) and a robust MockFootageProvider for test execution without external keys. Never pretend mock footage is production stock footage.
3. **Whisper Model Footprint:**
   - Loading large AI models can consume significant memory and time.
   - *Mitigation:* Default to `faster-whisper` `tiny` or `base` for lightning-fast, high-accuracy CPU execution, with configurable model size via environment variables (`WHISPER_MODEL=base`).
