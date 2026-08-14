from dotenv import load_dotenv  # type: ignore[import-not-found]
from fastapi import FastAPI

load_dotenv()

app = FastAPI()


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
