import asyncio
import threading
from typing import Any, Dict
from redis import Redis
from rq import Queue
from backend.app.config.settings import settings
from backend.app.core.logging import logger
from backend.app.db.session import SessionLocal
from backend.app.models.job import Job
from backend.app.services.pipeline import VideoEnginePipeline


def execute_job_task(job_id: str, is_mock: bool = False):
    """Entry point for worker background task execution."""
    logger.info(f"Worker executing job {job_id} (is_mock={is_mock})")
    pipeline = VideoEnginePipeline(job_id=job_id, is_mock=is_mock)
    try:
        # Run async pipeline in sync worker context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(pipeline.run())
        loop.close()
        return result
    except Exception as e:
        logger.error(f"Job {job_id} failed with error: {e}", exc_info=True)
        db = SessionLocal()
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = "failed"
                job.stage = "failed"
                job.error = {
                    "code": getattr(e, "code", "EXECUTION_ERROR"),
                    "message": str(e),
                    "retryable": getattr(e, "retryable", False),
                    "details": getattr(e, "details", {}),
                }
                db.commit()
        finally:
            db.close()
        raise


class JobQueueService:
    """Manages enqueueing and background execution of video generation jobs."""

    def __init__(self):
        self.redis_conn = None
        self.rq_queue = None
        try:
            self.redis_conn = Redis.from_url(settings.REDIS_URL, socket_connect_timeout=1)
            self.redis_conn.ping()
            self.rq_queue = Queue(settings.QUEUE_NAME, connection=self.redis_conn)
            logger.info("Connected to Redis RQ background queue")
        except Exception as e:
            logger.warning(f"Redis not available ({e}); using asynchronous in-process thread executor for local dev/testing")

    def enqueue_job(self, job_id: str, is_mock: bool = False) -> str:
        if settings.APP_ENV == "test":
            return f"test-queued-{job_id}"

        if self.rq_queue:
            job = self.rq_queue.enqueue(
                execute_job_task,
                job_id,
                is_mock,
                job_timeout=settings.JOB_TIMEOUT_SECONDS,
            )
            return job.get_id()
        else:
            # Local background thread fallback
            thread = threading.Thread(
                target=execute_job_task,
                args=(job_id, is_mock),
                daemon=True,
            )
            thread.start()
            return f"thread-{job_id}"


_queue_service = None


def get_queue_service() -> JobQueueService:
    global _queue_service
    if _queue_service is None:
        _queue_service = JobQueueService()
    return _queue_service
