# Sources & Dependencies Inventory — BrollForge

This document lists all software libraries, machine learning models, stock footage providers, media assets, and external services utilized in BrollForge, along with their commercial-use status and license verification.

---

## 1. Libraries & Frameworks

| Name | Version | Purpose | Source URL | License | Commercial-Use Status | Restrictions / Notes |
|---|---|---|---|---|---|---|
| **FastAPI** | >=0.111.0 | REST API Framework | https://fastapi.tiangolo.com/ | MIT License | Permitted | Standard web framework |
| **Uvicorn** | >=0.30.0 | ASGI Server | https://www.uvicorn.org/ | BSD-3-Clause | Permitted | Production server runtime |
| **Pydantic** | >=2.7.0 | Data validation & schemas | https://docs.pydantic.dev/ | MIT License | Permitted | Strict typed schemas |
| **SQLAlchemy** | >=2.0.30 | SQL ORM & query builder | https://www.sqlalchemy.org/ | MIT License | Permitted | PostgreSQL / SQLite support |
| **Redis** | >=5.0.4 | In-memory broker client | https://github.com/redis/redis-py | MIT License | Permitted | Connection to Redis queue |
| **RQ (Redis Queue)** | >=1.16.2 | Asynchronous job execution | https://python-rq.org/ | BSD-2-Clause | Permitted | Background pipeline jobs |
| **FFmpeg** | 9.1-full_build | Video encoding & muxing | https://www.ffmpeg.org/ / https://www.gyan.dev/ | GPL v3 / LGPL v3 | Permitted | Video manipulation binary |
| **FFprobe** | 9.1-full_build | Media stream probing | https://www.ffmpeg.org/ | GPL v3 / LGPL v3 | Permitted | Duration and codec inspection |
| **faster-whisper** | >=1.0.2 | Speech-to-text transcription | https://github.com/SYSTRAN/faster-whisper | MIT License | Permitted | CTranslate2-accelerated STT |
| **edge-tts** | >=6.1.12 | Neural Text-To-Speech | https://github.com/rany2/edge-tts | Python Software License | Permitted | High-quality Indian & global voices |
| **Scikit-learn** | >=1.4.2 | TF-IDF & Cosine Similarity | https://scikit-learn.org/ | BSD-3-Clause | Permitted | Semantic feature matching |
| **Boto3** | >=1.34.100 | S3 / MinIO storage client | https://github.com/boto/boto3 | Apache 2.0 | Permitted | Artifact archival |
| **HTTPX** | >=0.27.0 | Async HTTP client | https://www.python-httpx.org/ | BSD-3-Clause | Permitted | Safe external API requests |
| **React** | 18.3.1 | Web frontend library | https://react.dev/ | MIT License | Permitted | Component architecture |
| **Tailwind CSS** | 3.4.3 | Utility CSS styling | https://tailwindcss.com/ | MIT License | Permitted | Responsive dark UI |
| **Vite** | 5.2.11 | Frontend bundler | https://vitejs.dev/ | MIT License | Permitted | Fast HMR & build engine |

---

## 2. Machine Learning & Speech Models

| Model Name | Version / Weights | Purpose | Source / Creator | License | Commercial-Use Status |
|---|---|---|---|---|---|
| **Whisper Base** | OpenAI Whisper v3 weights | Speech-to-Text & Word Timestamps | OpenAI / Systran | MIT License | Permitted for commercial applications |
| **Microsoft Neural TTS** | Azure/Edge Neural (`en-IN-NeerjaNeural`, etc.) | Voiceover Narration Synthesis | Microsoft Speech Services | Microsoft Service Terms | Permitted for synthesized media delivery |

---

## 3. Stock Footage Providers & Licensing

| Provider Name | Role | API Endpoint | Commercial Terms URL | License | Commercial Status |
|---|---|---|---|---|---|
| **Pexels API** | Primary Stock Footage | `https://api.pexels.com/videos/search` | https://www.pexels.com/license/ | Pexels License | Explicitly allows commercial use, modifications, no watermark, no required attribution. |
| **Wikimedia Commons** | Secondary Stock Footage | `https://commons.wikimedia.org/w/api.php` | https://commons.wikimedia.org/wiki/Commons:Licensing | CC0 1.0 & CC-BY 4.0 | Fully commercial-clean; all non-commercial (NC) licenses are rejected. |
| **Local Licensed Pack** | Verified Fallback Catalog | Local disk (`./storage/licensed_footage_pack`) | https://creativecommons.org/publicdomain/zero/1.0/ | CC0 1.0 Universal Public Domain Dedication | 100% royalty-free, commercial use guaranteed without network dependency. |
| **Mock Provider** | Test Automation Fixture | `test_mock_provider` | Internal | Test License Only | Clearly marked as internal fixture; never represented as production stock. |
