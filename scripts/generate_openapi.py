import json
import sys
from pathlib import Path

from app.main import app


def generate_openapi(output_path: str = "openapi.json") -> None:
    with Path(output_path).open("w", encoding="utf-8") as file:
        json.dump(app.openapi(), file, indent=2)
        file.write("\n")


if __name__ == "__main__":
    output_path = sys.argv[1] if len(sys.argv) > 1 else "openapi.json"
    generate_openapi(output_path)
