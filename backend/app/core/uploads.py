"""Upload hardening: size caps and magic-byte MIME sniffing.

The client-supplied `content_type` is trusted only as a hint; the actual
file bytes are verified against known signatures before the upload is
accepted. Files that exceed the configured cap are rejected with 413.
"""

from __future__ import annotations

from fastapi import HTTPException, UploadFile, status

ALLOWED_IMAGE_TYPES: dict[str, bytes] = {
    "image/jpeg": b"\xff\xd8\xff",
    "image/png": b"\x89PNG\r\n\x1a\n",
    "image/webp": b"RIFF",
    "application/pdf": b"%PDF-",
}

_CHUNK_SIZE = 8192


async def read_upload_with_cap(file: UploadFile, max_bytes: int) -> bytes:
    """Read an UploadFile into memory, rejecting files larger than max_bytes."""
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(_CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"File exceeds the maximum allowed size of {max_bytes} bytes.",
            )
        chunks.append(chunk)
    return b"".join(chunks)


def read_upload_with_cap_sync(file: UploadFile, max_bytes: int) -> bytes:
    """Synchronous variant for sync endpoints; same size cap and 413 semantics."""
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = file.file.read(_CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"File exceeds the maximum allowed size of {max_bytes} bytes.",
            )
        chunks.append(chunk)
    return b"".join(chunks)


def sniff_mime_type(data: bytes, declared: str | None) -> str:
    """Return the canonical content type if the magic bytes match, else 415.

    Requires the full magic prefix for the declared type and does not trust
    the client-supplied Content-Type header.
    """
    if declared not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Upload type '{declared}' is not allowed. Accepted: JPEG, PNG, WebP, PDF.",
        )

    signature = ALLOWED_IMAGE_TYPES[declared]
    matches = data.startswith(signature)
    if declared == "image/webp":
        matches = matches and data[8:12] == b"WEBP"

    if not matches:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="The uploaded file's contents do not match its declared MIME type.",
        )
    return declared
