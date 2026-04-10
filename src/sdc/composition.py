"""Pydantic models and builder for FHIR Composition extraction templates.

Supports SDC template-based extraction (templateExtract).
"""

from __future__ import annotations

from collections.abc import Callable

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


# --- Tree traversal ---


def find_section(
    sections: list[CompositionSection], title: str
) -> CompositionSection | None:
    """Recursively find a section by title."""
    for s in sections:
        if s.title == title:
            return s
        if s.section:
            found = find_section(s.section, title)
            if found is not None:
                return found
    return None


def _map_sections(
    sections: list[CompositionSection],
    title: str,
    fn: Callable[[CompositionSection], CompositionSection],
) -> list[CompositionSection]:
    """Apply *fn* to the section matching *title*, recursively. Returns new list."""
    result: list[CompositionSection] = []
    for s in sections:
        if s.title == title:
            result.append(fn(s))
        elif s.section:
            result.append(
                s.model_copy(
                    update={"section": _map_sections(s.section, title, fn)}
                )
            )
        else:
            result.append(s)
    return result


def _has_title(sections: list[CompositionSection], title: str) -> bool:
    """Check if any section in the tree has the given title."""
    return find_section(sections, title) is not None


# --- Transform functions ---


def add_section(
    c: Composition,
    new_section: CompositionSection,
    parent_title: str | None = None,
) -> Composition:
    """Add a section to the Composition. Nest under *parent_title* if given."""
    sections = list(c.section or [])

    if new_section.title and _has_title(sections, new_section.title):
        raise ValueError(
            f"Section with title '{new_section.title}' already exists."
        )

    if parent_title is None:
        sections.append(new_section)
        return c.model_copy(update={"section": sections})

    if not _has_title(sections, parent_title):
        raise ValueError(f"Parent section '{parent_title}' not found.")

    def _append_child(s: CompositionSection) -> CompositionSection:
        children = list(s.section or [])
        children.append(new_section)
        return s.model_copy(update={"section": children})

    return c.model_copy(
        update={"section": _map_sections(sections, parent_title, _append_child)}
    )


def set_section_context(
    c: Composition, title: str, context: str
) -> Composition:
    """Set or update the templateExtractContext on a section."""
    sections = list(c.section or [])
    if not _has_title(sections, title):
        raise ValueError(f"Section '{title}' not found.")

    def _set_ctx(s: CompositionSection) -> CompositionSection:
        ctx_ext = Extension.model_validate(
            {"url": TEMPLATE_EXTRACT_CONTEXT_URL, "valueString": context}
        )
        # Replace existing context extension or add new one
        exts = [
            e for e in (s.extension or [])
            if e.url != TEMPLATE_EXTRACT_CONTEXT_URL
        ]
        exts.append(ctx_ext)
        return s.model_copy(update={"extension": exts})

    return c.model_copy(
        update={"section": _map_sections(sections, title, _set_ctx)}
    )


def set_section_text(c: Composition, title: str, text: str) -> Composition:
    """Set or update the Narrative text on a section. Auto-wraps in XHTML div."""
    sections = list(c.section or [])
    if not _has_title(sections, title):
        raise ValueError(f"Section '{title}' not found.")

    def _set_text(s: CompositionSection) -> CompositionSection:
        narrative = Narrative(
            div=f'<div xmlns="http://www.w3.org/1999/xhtml">{text}</div>'
        )
        return s.model_copy(update={"text": narrative})

    return c.model_copy(
        update={"section": _map_sections(sections, title, _set_text)}
    )
