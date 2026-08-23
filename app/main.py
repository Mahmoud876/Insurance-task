from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.errors import (
    http_exception_handler,
    validation_exception_handler,
)

from app.api.routes.claims import router as claims_router


load_dotenv()

app = FastAPI()

app.add_exception_handler(
    StarletteHTTPException,
    http_exception_handler,
)

app.add_exception_handler(
    RequestValidationError,
    validation_exception_handler,
)

app.include_router(claims_router, prefix="/v1")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


