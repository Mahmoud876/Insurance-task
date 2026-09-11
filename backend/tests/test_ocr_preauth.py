from io import BytesIO

import pytest
from fastapi import HTTPException, UploadFile
from starlette.datastructures import Headers

from app.config import settings
from app.main import app
from app.modules.ocr.api.ocr import process_card_ocr
from app.modules.preauth.api.preauth import _parse_uuid


def upload(content_type: str) -> UploadFile:
    return UploadFile(
        file=BytesIO(b"insurance-card"),
        filename="card.png",
        headers=Headers({"content-type": content_type}),
    )


@pytest.mark.anyio
async def test_ocr_returns_mock_in_development(monkeypatch) -> None:
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    response = await process_card_ocr(upload("image/png"))
    assert response.payer_id == "DEL_9981"
    assert response.confidence_score == 0.96


@pytest.mark.anyio
async def test_ocr_returns_501_in_production(monkeypatch) -> None:
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    with pytest.raises(HTTPException) as exc_info:
        await process_card_ocr(upload("image/png"))
    assert exc_info.value.status_code == 501


@pytest.mark.anyio
async def test_ocr_rejects_unsupported_media(monkeypatch) -> None:
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    with pytest.raises(HTTPException) as exc_info:
        await process_card_ocr(upload("text/plain"))
    assert exc_info.value.status_code == 415


def test_preauth_uuid_validation() -> None:
    with pytest.raises(HTTPException) as exc_info:
        _parse_uuid("not-a-uuid", "claim_id")
    assert exc_info.value.status_code == 422


def test_ocr_and_preauth_routes_are_registered() -> None:
    paths = app.openapi()["paths"]
    assert "/api/v1/insurance-cards/ocr" in paths
    assert "/api/v1/preauth/requests" in paths
    assert "/api/v1/preauth/requests/{preauth_id}" in paths
