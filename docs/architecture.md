# BrollForge Architecture & System Design

## 1. Architectural Overview
BrollForge is structured as a decoupled, multi-stage, event-driven video generation engine.

```
[ User Input: Audio/Script ]
            |
            v
+-----------------------+     +-------------------+
|  FastAPI REST Server  | <-> | Database (SQLAlchemy)|
+-----------------------+     +-------------------+
            |
            | Enqueue (Idempotent)
            v
+-----------------------+
|  Redis / In-Proc Queue|
+-----------------------+
            |
            v
+-----------------------------------------------------------+
|               Asynchronous Worker Pipeline                |
|                                                           |
| 1. Audio Ingestion / Edge-TTS Generation                  |
| 2. Media Probe & Silence Analysis (FFprobe)               |
| 3. Speech-to-Text with Timestamps (faster-whisper)        |
| 4. Meaning-Based Scene Segmentation & Metaphor Engine     |
| 5. Multi-Source Resilient Footage Acquisition             |
|    - Primary: Pexels API                                  |
|    - Secondary: Wikimedia Commons                         |
|    - Tertiary: Local Verified CC0 Pack                    |
| 6. Semantic Ranking & Zero-Duplicate Filter (TF-IDF/Cos)  |
| 7. Aspect-Ratio Normalization (16:9, 9:16, 1:1, 30fps)    |
| 8. SRT Subtitles & Burn-in Subtitles Filter               |
| 9. Audio Mux & Normalization (H.264 / AAC)                |
| 10. Metadata Artifacts: timeline.json & manifest.json     |
| 11. HMAC-SHA256 Webhook Notification                      |
+-----------------------------------------------------------+
```

## 2. Core Subsystems

### A. Meaning-Based Segmentation
Unlike naive fixed-interval chunking, BrollForge evaluates the linguistic semantics of each sentence and phrase. Long sentences are split along punctuation and clause pauses, while short utterances are coalesced to prevent flashing clips below 2.0 seconds.

### B. Disambiguation & Abstract Metaphor Engine
- **Abstract statements** like *"Trust is earned slowly"* are mapped to concrete, non-misleading visual metaphors (handshakes, joint craftsmanship).
- **Statistical statements** like *"Sales grew 40% in 2025"* are mapped to corporate analytics and strategic team discussions.
- **Polysemous words** are disambiguated:
  - *Cloud* -> Data center server racks with blue LEDs, not weather clouds.
  - *Bank* -> Financial institution office, not a riverbank.
  - *Python* -> Code editor and developer terminal, not a reptile.
  - *Mouse* -> Desktop computer mouse, not a rodent.

### C. Footage Licensing & Safety Isolation
- Candidates must possess verifiable commercial license terms (CC0, Pexels, CC-BY).
- Non-commercial licenses (NC) and watermarked footage are rejected.
- Avoid rules (faces, logos, violence) are applied as strict filtering constraints.
- Real people likenesses and brand logos are never fabricated.

### D. Rendering & Multi-Ratio Normalization
FFmpeg 9.1 is utilized with hardware/software optimizations:
- 16:9: `1920x1080`, SAR=1, 30 fps
- 9:16: `1080x1920`, smart centered crop without distortion, SAR=1, 30 fps
- 1:1: `1080x1080`, center crop, SAR=1, 30 fps
- Video codec: `libx264`, `yuv420p`
- Audio codec: `aac`, stereo 192k
