# api_docs.py
# Lightweight docs endpoints using Swagger UI via CDN (no extra deps).
from flask import Blueprint, Response

from openapi_spec import OPENAPI_SPEC

openapi_bp = Blueprint("openapi_spec", __name__)
docs_bp = Blueprint("docs", __name__)

@openapi_bp.route("/openapi.json", methods=["GET"])
def openapi_json():
    # Serve the in-memory OpenAPI spec as JSON.
    from json import dumps
    return Response(dumps(OPENAPI_SPEC), mimetype="application/json")

@docs_bp.route("/docs", methods=["GET"])
def swagger_ui():
    # Simple Swagger UI page that points to /openapi.json
    html = """<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <title>Safe Python Exec — API Docs</title>
    <link rel="stylesheet"
      href="https://unpkg.com/swagger-ui-dist@5.17.14/swagger-ui.css">
  </head>
  <body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5.17.14/swagger-ui-bundle.js"></script>
    <script>
      window.onload = () => {
        window.ui = SwaggerUIBundle({
          url: '/openapi.json',
          dom_id: '#swagger-ui',
          deepLinking: true,
          presets: [SwaggerUIBundle.presets.apis],
          layout: "BaseLayout"
        });
      };
    </script>
  </body>
</html>"""
    return Response(html, mimetype="text/html")
