"""Upload hardening: magic-byte MIME sniffing and size caps."""

from io import BytesIO

import pytest
from fastapi import HTTPException, UploadFile
from starlette.datastructures import Headers

from app.config import settings
from app.core.uploads import read_upload_with_cap, read_upload_with_cap_sync, sniff_mime_type

PNG_HEADER = b"\x89PNG\r\n\x1a\n"
JPEG_HEADER = b"\xff\xd8\xff\xe0"
PDF_HEADER = b"%PDF-1.7\n"
WEBP_HEADER = b"RIFF\x00\x00\x00\x00WEBPVP8"


def _upload(data: bytes, content_type: str) -> UploadFile:
    return UploadFile(
        file=BytesIO(data),
        filename="upload.bin",
        headers=Headers({"content-type": content_type}),
    )


@pytest.mark.parametrize(
    ("header", "mime"),
    [
        (PNG_HEADER, "image/png"),
        (JPEG_HEADER, "image/jpeg"),
        (PDF_HEADER, "application/pdf"),
        (WEBP_HEADER, "image/webp"),
    ],
)
def test_sniff_accepts_valid_magic(header: bytes, mime: str) -> None:
    assert sniff_mime_type(header + b"payload", mime) == mime


def test_sniff_rejects_declared_but_mismatched_bytes() -> None:
    with pytest.raises(HTTPException) as exc_info:
        sniff_mime_type(JPEG_HEADER + b"payload", "image/png")
    assert exc_info.value.status_code == 415


def test_sniff_rejects_unallowed_type() -> None:
    with pytest.raises(HTTPException) as exc_info:
        sniff_mime_type(b"anything", "text/plain")
    assert exc_info.value.status_code == 415


@pytest.mark.anyio
async def test_read_upload_with_cap_allows_under_cap() -> None:
    data = b"x" * 100
    result = await read_upload_with_cap(_upload(data, "image/png"), 1024)
    assert result == data


@pytest.mark.anyio
async def test_read_upload_with_cap_rejects_over_cap() -> None:
    upload = _upload(b"x" * 2048, "image/png")
    with pytest.raises(HTTPException) as exc_info:
        await read_upload_with_cap(upload, 1024)
    assert exc_info.value.status_code == 413


def test_read_upload_with_cap_sync_rejects_over_cap() -> None:
    upload = _upload(b"x" * 2048, "image/png")
    with pytest.raises(HTTPException) as exc_info:
        read_upload_with_cap_sync(upload, 1024)
    assert exc_info.value.status_code == 413


def test_upload_size_setting_is_sane() -> None:
    assert settings.MAX_UPLOAD_SIZE_BYTES >= 1024 * 1024
