# BrollForge REST API Reference

All application endpoints are served under `/api/v1/` (plus `/health` and `/ready`).

---

## 1. Job Creation

### `POST /api/v1/broll/jobs`
Accepts a JSON payload to start video generation from text script or audio URL.

#### Headers
- `Content-Type: application/json`
- `Idempotency-Key` *(optional)*: Unique string to guarantee safe retries.

#### Request Body
```json
{
  "script": "Trust is earned slowly. Sales grew 40% in 2025 as modern teams embraced cloud computing.",
  "audio_url": null,
  "scenes": null,
  "voice": "en-IN-female",
  "aspect_ratios": ["16:9", "9:16", "1:1"],
  "style": "bright, modern, real-world footage",
  "avoid": ["people's faces", "alcohol", "violence", "logos"],
  "captions": {
    "burn_in": true,
    "srt": true
  },
  "callback_url": null
}
```

#### Response: `202 Accepted`
```json
{
  "job_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "status": "queued",
  "progress": 0,
  "stage": "queued",
  "created_at": "2026-11-23T01:50:00Z",
  "updated_at": "2026-11-23T01:50:00Z",
  "result_links": {},
  "warnings": [],
  "error": null
}
```

---

### `POST /api/v1/broll/jobs/upload`
Upload an audio voiceover file (`.mp3`, `.wav`, or `.m4a`, up to 10 minutes).

#### Form Data
- `file`: Audio binary
- `aspect_ratios`: JSON array string `["16:9", "9:16"]`
- `style`: Visual style prompt string
- `avoid`: JSON array string `["people's faces", "alcohol"]`
- `burn_captions`: boolean (`true`/`false`)
- `callback_url`: optional URL string

---

## 2. Job Status & Results

### `GET /api/v1/jobs/{job_id}`
Returns real-time status and progress (0–100%).

#### Response: `200 OK`
```json
{
  "job_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "status": "succeeded",
  "progress": 100,
  "stage": "completed",
  "created_at": "2026-11-23T01:50:00Z",
  "updated_at": "2026-11-23T01:50:35Z",
  "result_links": {
    "videos": {
      "16:9": {
        "url": "/api/v1/storage/jobs/9b1deb4d/brollforge_9b1deb4d_16_9.mp4",
        "width": 1920,
        "height": 1080,
        "duration": 14.5,
        "file_size": 4821034,
        "aspect_ratio": "16:9"
      }
    },
    "timeline": "/api/v1/storage/jobs/9b1deb4d/timeline.json",
    "manifest": "/api/v1/storage/jobs/9b1deb4d/manifest.json",
    "captions_srt": "/api/v1/storage/jobs/9b1deb4d/captions.srt"
  },
  "warnings": [],
  "error": null
}
```

---

### `GET /api/v1/jobs`
List recent jobs with pagination (`?limit=20&offset=0`).

### `GET /api/v1/jobs/{job_id}/timeline`
Returns the complete `timeline.json` breakdown.

### `GET /api/v1/jobs/{job_id}/manifest`
Returns the standardized `manifest.json` artifact.

### `GET /api/v1/jobs/{job_id}/captions`
Downloads `captions.srt`.

---

## 3. Clip Swapping (Advanced Feature 16.B)

### `POST /api/v1/jobs/{job_id}/scenes/{scene_id}/swap`
Replaces the selected stock clip for a single scene and rerenders only that segment in seconds.

#### Request Body
```json
{
  "clip_id": null,
  "visual_hint": "modern software engineering dual monitor workstation"
}
```

#### Response: `200 OK`
```json
{
  "job_id": "9b1deb4d",
  "scene_id": "scene_1_abc123",
  "swap_time_seconds": 3.82,
  "before_clip": "raw_scene_1_old.mp4",
  "after_clip": "raw_swap_1_new.mp4",
  "result_links": { ... }
}
```

---

## 4. System & Health

### `GET /health`
Returns application health: `{"status": "healthy", "version": "1.0.0"}`.

### `GET /ready`
Returns dependency readiness (Database, Storage, Worker).

### `GET /api/v1/providers`
Lists configured footage providers and their commercial licensing verification status.

### `GET /api/v1/config`
Returns public configuration, supported aspect ratios, and voice options.

---

## 5. Standard Error Format (Point 5)
```json
{
  "error": {
    "code": "UPPER_SNAKE_CASE",
    "message": "Human-readable explanation",
    "retryable": false,
    "details": {}
  }
}
```
