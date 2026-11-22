import uuid
from fastapi import status


def test_health_and_readiness(client):
    res = client.get("/health")
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["status"] == "healthy"
    assert data["app"] == "BrollForge"

    res = client.get("/ready")
    assert res.status_code in {status.HTTP_200_OK, status.HTTP_503_SERVICE_UNAVAILABLE}
    data = res.json()
    assert "database" in data
    assert "storage" in data


def test_system_config_and_providers(client):
    res = client.get("/api/v1/config")
    assert res.status_code == status.HTTP_200_OK
    cfg = res.json()
    assert "supported_aspect_ratios" in cfg
    assert "en-IN-female" in [v["id"] for v in cfg["supported_voices"]]

    res = client.get("/api/v1/providers")
    assert res.status_code == status.HTTP_200_OK
    prov = res.json()
    assert "primary_provider" in prov
    assert "secondary_provider" in prov
    assert "local_licensed_pack" in prov


def test_job_submission_and_idempotency(client):
    idempotency_key = f"test-key-{uuid.uuid4()}"
    payload = {
        "script": "Testing BrollForge video pipeline with automated API integration tests.",
        "voice": "en-IN-female",
        "aspect_ratios": ["16:9", "9:16"],
        "style": "bright, modern, real-world footage",
        "avoid": ["alcohol", "violence"],
        "captions": {"burn_in": True, "srt": True},
    }

    # 1. Initial job submission -> HTTP 202
    res = client.post("/api/v1/broll/jobs", json=payload, headers={"Idempotency-Key": idempotency_key})
    assert res.status_code == status.HTTP_202_ACCEPTED
    data = res.json()
    job_id = data["job_id"]
    assert job_id is not None
    assert data["status"] in {"queued", "running", "succeeded"}

    # 2. Re-submit same idempotency key with SAME payload -> returns existing job (HTTP 200 or 202)
    res_retry = client.post("/api/v1/broll/jobs", json=payload, headers={"Idempotency-Key": idempotency_key})
    assert res_retry.status_code in {status.HTTP_200_OK, status.HTTP_202_ACCEPTED}
    data_retry = res_retry.json()
    assert data_retry["job_id"] == job_id

    # 3. Re-submit same key with DIFFERENT payload -> HTTP 409 Conflict
    diff_payload = dict(payload, script="Completely different script content.")
    res_conflict = client.post("/api/v1/broll/jobs", json=diff_payload, headers={"Idempotency-Key": idempotency_key})
    assert res_conflict.status_code == status.HTTP_409_CONFLICT
    err_data = res_conflict.json()
    assert err_data["error"]["code"] == "IDEMPOTENCY_KEY_MISMATCH"


def test_ssrf_protection(client):
    # Prohibit local IP and loopback
    res = client.post("/api/v1/broll/jobs", json={"audio_url": "http://127.0.0.1:8000/secret.mp3"})
    assert res.status_code == status.HTTP_400_BAD_REQUEST
    data = res.json()
    assert data["error"]["code"] == "SSRF_SECURITY_VIOLATION"

    # Prohibit cloud metadata endpoint
    res2 = client.post("/api/v1/broll/jobs", json={"audio_url": "http://169.254.169.254/latest/meta-data/"})
    assert res2.status_code == status.HTTP_400_BAD_REQUEST
    data2 = res2.json()
    assert data2["error"]["code"] == "SSRF_SECURITY_VIOLATION"


def test_job_query_endpoints(client):
    res = client.get("/api/v1/jobs")
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert "total" in data
    assert "jobs" in data

    # Non-existent job
    res_not_found = client.get(f"/api/v1/jobs/{uuid.uuid4()}")
    assert res_not_found.status_code == status.HTTP_404_NOT_FOUND
    assert res_not_found.json()["error"]["code"] == "JOB_NOT_FOUND"
