from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from app.config import settings


class OcrEngineUnavailableError(RuntimeError):
    """Raised when the OCR engine (or its optional system deps) are not installed."""


@dataclass(frozen=True)
class OcrLine:
    text: str
    confidence: float = 1.0
    y0: float = 0.0


class OcrEngine:
    def __init__(self, languages: Sequence[str] | None = None, gpu: bool = False) -> None:
        try:
            import easyocr
        except ImportError as exc:
            raise OcrEngineUnavailableError(
                "EasyOCR is not installed. Install the project with the 'ocr' extra "
                "(e.g. `uv sync --extra ocr` in the backend directory)."
            ) from exc
        self._reader = easyocr.Reader(list(languages or ["en"]), gpu=gpu, verbose=False)

    def text_lines(self, image: Any) -> list[OcrLine]:
        results = self._reader.readtext(image)
        lines = [
            OcrLine(text=str(text), confidence=float(confidence), y0=float(bbox[0][1]))
            for bbox, text, confidence in results
        ]
        lines.sort(key=lambda line: (line.y0, line.text.lower()))
        return lines


def image_from_bytes(data: bytes, media_type: str) -> Any:
    from io import BytesIO

    import numpy as np
    from PIL import Image

    if media_type == "application/pdf":
        import pypdfium2 as pdfium

        doc = pdfium.PdfDocument(data)
        try:
            page = doc[0]
            bitmap = page.render(scale=200 / 72)
            pil_image = bitmap.to_pil()
        finally:
            doc.close()
        return np.asarray(pil_image.convert("RGB"))

    with Image.open(BytesIO(data)) as img:
        return np.asarray(img.convert("RGB"))


_engine: OcrEngine | None = None


def get_ocr_engine() -> OcrEngine:
    global _engine
    if not settings.OCR_ENABLED:
        raise OcrEngineUnavailableError("OCR is disabled by configuration.")
    if _engine is None:
        languages = [
            lang.strip() for lang in settings.OCR_LANGUAGES.split(",") if lang.strip()
        ] or ["en"]
        _engine = OcrEngine(languages=languages, gpu=settings.OCR_GPU)
    return _engine
