import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OPENAPI_PATH = ROOT / "openapi.json"
OUTPUT_PATH = ROOT / "frontend" / "src" / "mocks" / "handlers.js"


def main() -> None:
    spec = json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))

    handlers = []

    for path, path_item in spec.get("paths", {}).items():
        for method in path_item:
            if method.lower() not in {
                "get",
                "post",
                "put",
                "patch",
                "delete",
            }:
                continue

            handlers.append(
                f"  http.{method.lower()}('{path.replace('{', ':').replace('}', '')}', async () => {{\n"
                "    return HttpResponse.json({});\n"
                "  }),"
            )

    content = """import {{ http, HttpResponse }} from 'msw'

export const handlers = [
{}
]
""".format("\n\n".join(handlers))

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
