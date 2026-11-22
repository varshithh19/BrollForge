from typing import Any, Dict, Optional
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse


class BrollForgeException(Exception):
    """Base exception for all BrollForge operational errors."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        retryable: bool = False,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.retryable = retryable
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "retryable": self.retryable,
                "details": self.details,
            }
        }


class ValidationError(BrollForgeException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            retryable=False,
            details=details,
        )


class SSRFSecurityError(BrollForgeException):
    def __init__(self, message: str = "Invalid or restricted URL target prohibited by SSRF security policy"):
        super().__init__(
            code="SSRF_SECURITY_VIOLATION",
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            retryable=False,
        )


class MediaProbeError(BrollForgeException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="MEDIA_PROBE_FAILED",
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            retryable=False,
            details=details,
        )


class SilentAudioError(BrollForgeException):
    def __init__(self, message: str = "Audio contains only silence or speech level is undetectable"):
        super().__init__(
            code="SILENT_AUDIO_DETECTED",
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            retryable=False,
        )


class MusicOnlyAudioError(BrollForgeException):
    def __init__(self, message: str = "Audio appears to be music-only with no discernible speech narration"):
        super().__init__(
            code="SPEECH_NOT_DETECTED",
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            retryable=False,
        )


class FootageNotFoundError(BrollForgeException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="FOOTAGE_NOT_FOUND",
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            retryable=True,
            details=details,
        )


class LicenseVerificationError(BrollForgeException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="LICENSE_VERIFICATION_FAILED",
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            retryable=False,
            details=details,
        )


class RenderingError(BrollForgeException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="RENDERING_PIPELINE_ERROR",
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            retryable=True,
            details=details,
        )


class IdempotencyConflictError(BrollForgeException):
    def __init__(self, message: str = "Idempotency key reused with mismatched request parameters"):
        super().__init__(
            code="IDEMPOTENCY_KEY_MISMATCH",
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            retryable=False,
        )


class JobNotFoundError(BrollForgeException):
    def __init__(self, job_id: str):
        super().__init__(
            code="JOB_NOT_FOUND",
            message=f"Job with ID '{job_id}' does not exist",
            status_code=status.HTTP_404_NOT_FOUND,
            retryable=False,
            details={"job_id": job_id},
        )


async def brollforge_exception_handler(request: Request, exc: BrollForgeException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred during processing",
                "retryable": True,
                "details": {"error_type": type(exc).__name__},
            }
        },
    )
