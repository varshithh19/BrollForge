# AI Use & Assistance Disclosure — BrollForge

In accordance with Section 22 of the IncuBrix Engineering Assessment specification, this document transparently discloses all AI tools, models, and assistants utilized during the architecture, development, and runtime execution of BrollForge.

---

## 1. Development & Engineering Assistant Disclosure
- **Tool Used:** Google Antigravity (Advanced Agentic Coding Assistant powered by Gemini 3.8 Flash / Thinking models).
- **Tasks Assisted:**
  - Architecting the end-to-end asynchronous 22-step processing pipeline.
  - Designing Pydantic v2 schemas for `timeline.json` and `manifest.json`.
  - Implementing FFmpeg 9.1 filter graphs for 16:9, 9:16, and 1:1 multi-ratio video normalization.
  - Structuring the meaning-based scene segmentation engine with domain metaphor disambiguation.
  - Writing the automated test suite covering unit tests, integration tests, E2E pipelines, and the 20 Hard Cases.
  - Authoring React 18 / Tailwind CSS frontend components and batch runner CLI tooling.

---

## 2. Models Used in the Application Runtime
BrollForge utilizes commercially clean, open or neural models for media synthesis and transcription:

1. **faster-whisper (Systran / OpenAI):**
   - **Model:** Whisper `base` (CTranslate2 optimized weights).
   - **License:** MIT License.
   - **Role:** Automatic Speech Recognition (ASR), word-level and segment-level timestamp extraction, and language identification.
   - **Verification:** Benchmarked on CPU int8 execution; generates truthful timestamps without hallucinating fake segments on silent or music-only audio.

2. **Edge Neural Text-To-Speech (Microsoft):**
   - **Model:** `en-IN-NeerjaNeural` (Indian English Female), `en-IN-PrabhatNeural` (Indian English Male), `en-US-AriaNeural`, `hi-IN-SwaraNeural`, `ta-IN-PallaviNeural`.
   - **Role:** High-fidelity voiceover synthesis from written scripts.
   - **Commercial Status:** Public neural interface; verified audio output delivered in standard PCM/MP3 format.

3. **TF-IDF & Cosine Similarity Embedding Engine (Scikit-Learn):**
   - **Model:** Deterministic sub-word n-gram vectorizer (BSD-3-Clause).
   - **Role:** Fast, zero-hallucination semantic matching between narration concepts and stock video candidate metadata.

---

## 3. Human & Automated Verification Performed
- **Zero Hallucinated Metrics:** Every metric in `manifest.json` and `timeline.json` (scene durations, relevance scores, turnaround times) is derived from real measured execution.
- **Media Validation via FFprobe:** All rendered videos are probed using `ffprobe` to verify video codec (`h264`), audio codec (`aac`), framerate (`30 fps`), and exact pixel dimensions (`1920x1080`, `1080x1920`, `1080x1080`).
- **Safety Filters:** Avoid rules prevent fabrication of realistic faces of real people or brand logos.
