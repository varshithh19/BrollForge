#!/usr/bin/env python3
"""
BrollForge Batch Runner CLI Tool (Integration Standard Point 10)
Accepts single input file or folder of inputs (scripts or audio), submits jobs to API,
tracks progress, downloads all artifacts, and generates a structured summary report with timings.
Supports both live HTTP API server and direct in-memory FastAPI mode.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx


def get_client(api_base: str, direct: bool = False):
    """Returns either an httpx.Client or a FastAPI TestClient."""
    if direct:
        from fastapi.testclient import TestClient
        from backend.app.main import app
        return TestClient(app)
    else:
        # Check if live server is reachable, fallback to direct if not
        try:
            with httpx.Client(timeout=1.5) as probe:
                probe.get(f"{api_base}/health")
            return httpx.Client(base_url=api_base, timeout=60.0)
        except Exception:
            print(f"[Notice] API server at {api_base} unreachable. Falling back to direct in-memory execution.")
            from fastapi.testclient import TestClient
            from backend.app.main import app
            return TestClient(app)


def submit_script_job(client, script_text: str, voice: str = "en-IN-female") -> str:
    url = "/api/v1/broll/jobs"
    payload = {
        "script": script_text,
        "voice": voice,
        "aspect_ratios": ["16:9", "9:16"],
        "style": "bright, modern, real-world footage",
        "avoid": ["people's faces", "alcohol", "violence"],
        "captions": {"burn_in": True, "srt": True},
    }
    headers = {"Idempotency-Key": f"batch-{int(time.time()*1000)}-{os.urandom(4).hex()}"}
    resp = client.post(url, json=payload, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    return data["job_id"]


def submit_audio_job(client, audio_file_path: str) -> str:
    url = "/api/v1/broll/jobs/upload"
    headers = {"Idempotency-Key": f"batch-{int(time.time()*1000)}-{os.urandom(4).hex()}"}
    with open(audio_file_path, "rb") as f:
        files = {"file": (Path(audio_file_path).name, f, "audio/mpeg")}
        data = {
            "aspect_ratios": json.dumps(["16:9", "9:16"]),
            "style": "bright, modern, real-world footage",
            "avoid": json.dumps(["people's faces", "alcohol"]),
            "burn_captions": "true",
        }
        resp = client.post(url, data=data, files=files, headers=headers)
        resp.raise_for_status()
        res = resp.json()
        return res["job_id"]


def wait_for_job(client, job_id: str, poll_interval: float = 2.0, timeout: float = 300.0) -> Dict[str, Any]:
    start = time.time()
    url = f"/api/v1/broll/jobs/{job_id}"
    while time.time() - start < timeout:
        resp = client.get(url)
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status")
        progress = data.get("progress", 0)
        stage = data.get("stage", "running")

        print(f"  [Job {job_id[:8]}] Status: {status} | Stage: {stage} | Progress: {progress}%", end="\r")

        if status in {"succeeded", "failed"}:
            print()  # newline
            return data

        time.sleep(poll_interval)

    raise TimeoutError(f"Job {job_id} timed out after {timeout} seconds")


def download_artifact(client, url: str, target_path: Path):
    target_path.parent.mkdir(parents=True, exist_ok=True)
    resp = client.get(url)
    resp.raise_for_status()
    with open(target_path, "wb") as f:
        f.write(resp.content)


def process_input(client, input_path: Path, output_root: Path) -> Dict[str, Any]:
    print(f"\nProcessing input: {input_path.name}")
    start_time = time.time()

    ext = input_path.suffix.lower()
    job_id = None

    if ext in {".txt", ".script"}:
        with open(input_path, "r", encoding="utf-8") as f:
            script_text = f.read().strip()
        job_id = submit_script_job(client, script_text)
    elif ext in {".json"}:
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            # IncuBrix structured scene list
            script_text = " ".join(item.get("text", "") for item in data)
            job_id = submit_script_job(client, script_text)
        elif isinstance(data, dict):
            script_text = data.get("script") or " ".join(item.get("text", "") for item in data.get("scenes", []))
            job_id = submit_script_job(client, script_text, voice=data.get("voice", "en-IN-female"))
    elif ext in {".mp3", ".wav", ".m4a"}:
        job_id = submit_audio_job(client, str(input_path))
    else:
        print(f"Skipping unsupported file extension: {ext}")
        return {"input": str(input_path), "status": "skipped", "reason": f"unsupported extension {ext}"}

    print(f"Submitted Job ID: {job_id}")

    job_data = wait_for_job(client, job_id)
    turnaround_time = round(time.time() - start_time, 2)

    # Save artifacts into structured job folder
    job_out_dir = output_root / job_id
    job_out_dir.mkdir(parents=True, exist_ok=True)

    with open(job_out_dir / "job_status.json", "w", encoding="utf-8") as f:
        json.dump(job_data, f, indent=2)

    if job_data.get("status") == "succeeded":
        result_links = job_data.get("result_links", {})

        # Download timeline & manifest
        if tl_url := result_links.get("timeline"):
            download_artifact(client, tl_url, job_out_dir / "timeline.json")
        if mf_url := result_links.get("manifest"):
            download_artifact(client, mf_url, job_out_dir / "manifest.json")
        if srt_url := result_links.get("captions_srt"):
            download_artifact(client, srt_url, job_out_dir / "captions.srt")

        # Download videos
        videos = result_links.get("videos", {})
        for ratio, v_info in videos.items():
            clean_ratio = ratio.replace(":", "_")
            v_url = v_info.get("url")
            if v_url:
                download_artifact(client, v_url, job_out_dir / f"video_{clean_ratio}.mp4")

        print(f"Successfully downloaded all outputs to: {job_out_dir}")

    return {
        "job_id": job_id,
        "input": str(input_path),
        "status": job_data.get("status"),
        "stage": job_data.get("stage"),
        "turnaround_time_seconds": turnaround_time,
        "error": job_data.get("error"),
        "output_directory": str(job_out_dir),
    }


def main():
    parser = argparse.ArgumentParser(description="BrollForge Batch Runner CLI")
    parser.add_argument("--input", required=True, help="Path to input file or directory of input files")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000", help="Base URL of BrollForge API")
    parser.add_argument("--output-dir", default="./test_outputs", help="Output directory for results")
    parser.add_argument("--direct", action="store_true", help="Run directly in-memory via FastAPI TestClient")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_root = Path(args.output_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        print(f"Error: input path '{input_path}' does not exist.")
        sys.exit(1)

    items_to_process = []
    if input_path.is_file():
        items_to_process.append(input_path)
    else:
        for p in input_path.iterdir():
            if p.is_file() and p.suffix.lower() in {".txt", ".json", ".mp3", ".wav", ".m4a"}:
                items_to_process.append(p)

    if not items_to_process:
        print(f"No valid audio or script files found in {input_path}")
        sys.exit(0)

    print(f"--- BrollForge Batch Runner Starting ({len(items_to_process)} inputs) ---")
    client = get_client(args.api_url, direct=args.direct)
    start_all = time.time()
    results = []

    for item in items_to_process:
        res = process_input(client, item, output_root)
        results.append(res)

    total_time = round(time.time() - start_all, 2)
    succeeded_count = sum(1 for r in results if r.get("status") == "succeeded")
    failed_count = sum(1 for r in results if r.get("status") == "failed")

    summary_report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_inputs": len(items_to_process),
        "succeeded": succeeded_count,
        "failed": failed_count,
        "total_turnaround_time_seconds": total_time,
        "average_turnaround_time_seconds": round(total_time / max(1, len(items_to_process)), 2),
        "jobs": results,
    }

    report_path = output_root / "batch_summary_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(summary_report, f, indent=2)

    print("\n================ BATCH RUNNER SUMMARY REPORT ================")
    print(f"Total Inputs: {len(items_to_process)}")
    print(f"Succeeded:    {succeeded_count}")
    print(f"Failed:       {failed_count}")
    print(f"Total Time:   {total_time}s")
    print(f"Avg Time:     {summary_report['average_turnaround_time_seconds']}s / input")
    print(f"Report Saved: {report_path}")
    print("=============================================================")


if __name__ == "__main__":
    main()
