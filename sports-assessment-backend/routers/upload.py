"""
upload.py – Router for video file uploads
POST /api/upload
"""

import os
import uuid
import aiofiles
from fastapi import APIRouter, UploadFile, File, HTTPException
from schemas import UploadResponse

router = APIRouter(prefix="/api", tags=["upload"])

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Allowed video MIME types
ALLOWED_MIME_TYPES = {
    "video/mp4", "video/webm", "video/x-matroska", "video/avi",
    "video/quicktime", "video/x-msvideo", "video/ogg",
}
MAX_FILE_SIZE_MB = 500


@router.post("/upload", response_model=UploadResponse)
async def upload_video(file: UploadFile = File(...)):
    """
    Accept a video file upload and save it to the uploads directory.
    Returns a file_id that must be passed to /api/process.
    """
    # Validate MIME type (best-effort — browsers may send 'application/octet-stream')
    content_type = file.content_type or ""
    if content_type and content_type not in ALLOWED_MIME_TYPES and "video" not in content_type:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type: {content_type}. Upload a video file (mp4, webm, avi, etc.).",
        )

    # Generate a unique file ID and preserve extension
    file_ext = os.path.splitext(file.filename or "upload.mp4")[1] or ".mp4"
    file_id = str(uuid.uuid4())
    save_path = os.path.join(UPLOAD_DIR, f"{file_id}{file_ext}")

    # Stream save to disk
    size_bytes = 0
    async with aiofiles.open(save_path, "wb") as out_file:
        while chunk := await file.read(1024 * 1024):  # 1 MB chunks
            size_bytes += len(chunk)
            if size_bytes > MAX_FILE_SIZE_MB * 1024 * 1024:
                await out_file.close()
                os.remove(save_path)
                raise HTTPException(
                    status_code=413,
                    detail=f"File exceeds maximum size of {MAX_FILE_SIZE_MB} MB.",
                )
            await out_file.write(chunk)

    return UploadResponse(
        file_id=file_id,
        filename=file.filename or f"{file_id}{file_ext}",
        size_bytes=size_bytes,
        message="Video uploaded successfully. Use the file_id to trigger analysis.",
    )
