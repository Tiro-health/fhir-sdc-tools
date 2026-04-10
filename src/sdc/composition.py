"""Pydantic models and builder for FHIR Composition extraction templates.

Supports SDC template-based extraction (templateExtract).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from sdc.models import Extension

# --- SDC Template Extraction URLs ---

TEMPLATE_EXTRACT_CONTEXT_URL = (
    "http://hl7.org/fhir/uv/sdc/StructureDefinition/"
    "sdc-questionnaire-templateExtractContext"
)
TEMPLATE_EXTRACT_URL = (
    "http://hl7.org/fhir/uv/sdc/StructureDefinition/"
    "sdc-questionnaire-templateExtract"
)
TEMPLATE_EXTRACT_PROFILE = (
    "http://hl7.org/fhir/uv/sdc/StructureDefinition/"
    "sdc-questionnaire-extr-template"
)

# --- Models ---

_MODEL_CONFIG = ConfigDict(extra="allow", populate_by_name=True)


class Narrative(BaseModel):
    model_config = _MODEL_CONFIG

    status: str = "generated"
    div: str


class CompositionSection(BaseModel):
    model_config = _MODEL_CONFIG

    title: str | None = None
    extension: list[Extension] | None = None
    text: Narrative | None = None
    section: list[CompositionSection] | None = None


class Composition(BaseModel):
    model_config = _MODEL_CONFIG

    resource_type: str = Field("Composition", alias="resourceType")
    id: str | None = None
    status: str = "final"
    type: dict[str, object]
    title: str | None = None
    date: str | None = None
    section: list[CompositionSection] | None = None


# --- Section builder ---


def section(
    *,
    title: str | None = None,
    context: str | None = None,
    text: str = "",
    children: list[CompositionSection] | None = None,
) -> CompositionSection:
    """Build a CompositionSection with optional templateExtractContext.

    Parameters
    ----------
    title:
        Section title.
    context:
        FHIRPath expression for templateExtractContext extension.
    text:
        Inner HTML content, auto-wrapped in an XHTML div.
    children:
        Nested sub-sections.
    """
    s = CompositionSection()
    if context:
        s.extension = [
            Extension.model_validate(
                {
                    "url": TEMPLATE_EXTRACT_CONTEXT_URL,
                    "valueString": context,
                }
            )
        ]
    if title:
        s.title = title
    if text:
        s.text = Narrative(
            div=f'<div xmlns="http://www.w3.org/1999/xhtml">{text}</div>'
        )
    if children:
        s.section = children
    return s
