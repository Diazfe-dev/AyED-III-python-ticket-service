"""Public API documentation: the hand-written OpenAPI contract and its Swagger UI page."""

from pathlib import Path

from flask import Blueprint, Response, current_app

bp = Blueprint("api_docs", __name__)

SWAGGER_UI_CDN = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14"
SWAGGER_UI_PAGE = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Ticket Service API</title>
    <link rel="stylesheet" href="{SWAGGER_UI_CDN}/swagger-ui.css">
  </head>
  <body>
    <div id="swagger-ui"></div>
    <script src="{SWAGGER_UI_CDN}/swagger-ui-bundle.js"></script>
    <script>
      SwaggerUIBundle({{url: "/openapi.json", dom_id: "#swagger-ui"}});
    </script>
  </body>
</html>
"""


def contract_path() -> Path:
    """Location of the OpenAPI contract, `docs/openapi.json` at the repository root."""
    return Path(current_app.root_path).parent / "docs" / "openapi.json"


@bp.get("/openapi.json")
def openapi_contract() -> Response:
    return Response(contract_path().read_bytes(), mimetype="application/json")


@bp.get("/docs")
def swagger_ui() -> Response:
    return Response(SWAGGER_UI_PAGE, mimetype="text/html")
