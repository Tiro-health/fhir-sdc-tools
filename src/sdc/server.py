"""MCP server that renders FHIR Questionnaires using the Tiro web-sdk."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult, TextContent

RESOURCE_URI = "ui://fhir-sdc-tools/questionnaire-app.html"
RESOURCE_MIME_TYPE = "text/html;profile=mcp-app"

CSP_CONFIG: dict[str, Any] = {
    "resourceDomains": ["https://cdn.tiro.health"],
    "connectDomains": ["https://sdc.tiro.health"],
}

UI_META: dict[str, Any] = {
    "ui": {
        "resourceUri": RESOURCE_URI,
        "csp": CSP_CONFIG,
    },
}

_HTML_PATH = Path(__file__).resolve().parent / "questionnaire-app.html"

server = FastMCP(
    name="Tiro.health FHIR SDC tools",
    log_level="WARNING",
)


@server.tool(
    name="render-questionnaire",
    title="Render FHIR Questionnaire",
    description=(
        "Renders an interactive FHIR Questionnaire form. "
        "Accepts a canonical questionnaire URL (resolved by the SDC server) "
        "or an inline FHIR Questionnaire JSON resource."
    ),
    meta=UI_META,
)
def render_questionnaire(
    questionnaire: str | dict[str, Any],
    sdc_endpoint: str | None = None,
    launch_context: dict[str, Any] | None = None,
    read_only: bool = False,
    submit_endpoint: str | None = None,
) -> CallToolResult:
    """Render a FHIR Questionnaire via the Tiro web-sdk."""
    if isinstance(questionnaire, str):
        label = questionnaire
    else:
        label = questionnaire.get("title", "Questionnaire")

    return CallToolResult(
        content=[TextContent(type="text", text=f"Rendering questionnaire: {label}")],
        structuredContent={
            "questionnaire": questionnaire,
            "sdcEndpoint": sdc_endpoint,
            "launchContext": launch_context,
            "readOnly": read_only,
            "submitEndpoint": submit_endpoint,
        },
    )


@server.resource(
    RESOURCE_URI,
    name="questionnaire-app",
    description="Bundled HTML app for rendering FHIR Questionnaires",
    mime_type=RESOURCE_MIME_TYPE,
    meta={"ui": {"csp": CSP_CONFIG}},
)
def questionnaire_app_html() -> str:
    """Read and return the bundled questionnaire HTML."""
    return _HTML_PATH.read_text(encoding="utf-8")


def main() -> None:
    """Run the MCP server (stdio transport by default)."""
    import os

    from mcp.server.fastmcp.server import TransportSecuritySettings

    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport == "streamable-http":
        server.settings.host = "0.0.0.0"
        server.settings.port = int(os.environ.get("PORT", "8080"))
        server.settings.transport_security = TransportSecuritySettings(
            enable_dns_rebinding_protection=False,
        )
    server.run(transport=transport)


if __name__ == "__main__":
    main()
