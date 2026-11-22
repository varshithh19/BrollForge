# Licensing & Commercial-Use Verification — BrollForge

This document details the licensing compliance and commercial-use status of all runtime dependencies, software components, and media footage providers used in BrollForge, conforming to Assessment Requirement 3 and Section 22.

---

## 1. Core Licensing Principles
BrollForge operates under strict commercial licensing compliance:
1. **Commercial Use Only:** Only libraries, models, and footage sources whose terms explicitly permit commercial deployment are utilized in production paths.
2. **Rejection of Non-Commercial Media:** Creative Commons Non-Commercial (`CC BY-NC`, `CC BY-NC-SA`, `CC BY-NC-ND`) assets are strictly rejected at the provider inspection layer.
3. **Zero Watermarks:** Watermarked footage and scraped unauthorized video streams are strictly prohibited.
4. **Verifiable Attribution:** Every rendered scene records creator attribution, license name, and canonical license URL in `timeline.json` and `manifest.json`.

---

## 2. Dependency Licensing Matrix

| Component | License Type | Commercial Use Permitted? | Attribution Required? | Notes |
|---|---|---|---|---|
| **Python Standard Library** | PSF License | **YES** | No | Standard language runtime |
| **FastAPI** | MIT License | **YES** | No | Standard permissive license |
| **Uvicorn** | BSD 3-Clause | **YES** | Yes (in source distributions) | Permissive server |
| **Pydantic v2** | MIT License | **YES** | No | Data validation |
| **SQLAlchemy 2** | MIT License | **YES** | No | Database ORM |
| **faster-whisper** | MIT License | **YES** | No | CTranslate2 Whisper implementation |
| **OpenAI Whisper Weights** | MIT License | **YES** | No | Official OpenAI model weights |
| **edge-tts** | Python Software License | **YES** | No | Speech synthesis adapter |
| **scikit-learn** | BSD 3-Clause | **YES** | Yes (in binary distributions) | Permissive ML framework |
| **FFmpeg (Gyan Build)** | GPL v3 / LGPL v3 | **YES** | Yes (source/binaries preserved) | Standalone CLI binary called via subprocess; no proprietary dynamic linking |
| **React & Vite** | MIT License | **YES** | No | Permissive frontend bundle |
| **Tailwind CSS** | MIT License | **YES** | No | Permissive utility CSS |

---

## 3. Footage Source Commercial Terms

### A. Pexels Video API (Primary Provider)
- **License Name:** Pexels License
- **License Terms URL:** https://www.pexels.com/license/
- **Commercial Status:** **VERIFIED COMMERCIAL USE ALLOWED**
- **Terms Summary:**
  - All videos on Pexels can be used for free.
  - Commercial and non-commercial use is allowed.
  - Attribution is not required (giving credit to the videographer or Pexels is not necessary but always appreciated and provided by BrollForge).
  - You can modify the videos.
  - Prohibited: Selling unaltered copies of a video; implying endorsements by people or brands.

### B. Wikimedia Commons (Secondary Provider)
- **License Names:** Creative Commons Zero (`CC0 1.0 Universal`), Creative Commons Attribution (`CC BY 4.0`), Public Domain
- **License Terms URL:** https://creativecommons.org/publicdomain/zero/1.0/ and https://creativecommons.org/licenses/by/4.0/
- **Commercial Status:** **VERIFIED COMMERCIAL USE ALLOWED**
- **Enforcement Rule:** BrollForge automatically scans `LicenseShortName` and rejects any candidate containing `NC`, `NON-COMMERCIAL`, or `NONCOMMERCIAL`.

### C. Local Licensed Footage Pack (Fallback Provider)
- **License Name:** Creative Commons Zero (`CC0 1.0 Universal`)
- **License Terms URL:** https://creativecommons.org/publicdomain/zero/1.0/
- **Commercial Status:** **100% PUBLIC DOMAIN DEDICATION**
- **Terms Summary:** Free for commercial use, modification, distribution, without any royalty or copyright restrictions.

### D. Automated Test Fixtures (Mock Provider)
- **License:** Internal QA Fixture License (MIT)
- **Scope:** Restricted to test execution (`APP_ENV=test`); explicitly labeled as non-production fixture in output metadata.
