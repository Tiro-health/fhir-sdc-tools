"""FHIRPath expression helpers for SDC template-based extraction.

Pure string functions — no models, no IO.
"""

from __future__ import annotations


def coding(system: str, code: str) -> str:
    """Create a FHIRPath coding literal."""
    return f"%factory.Coding('{system}', '{code}')"


def item_path(link_id: str) -> str:
    """Navigate to a questionnaire item by linkId."""
    return f"item.where(linkId='{link_id}')"


def answer_value(link_id: str, prop: str | None = None) -> str:
    """Extract the answer value for a given linkId, with optional property."""
    suffix = f".{prop}" if prop else ""
    return f"item.where(linkId='{link_id}').answer.value{suffix}"


def nested_answer_value(
    parent_link_id: str, child_link_id: str, prop: str | None = None
) -> str:
    """Extract answer value from an enableWhen-nested item."""
    suffix = f".{prop}" if prop else ""
    return (
        f"item.where(linkId='{parent_link_id}').answer.item"
        f".where(linkId='{child_link_id}').answer.value{suffix}"
    )


def placeholder(expr: str) -> str:
    """Wrap a FHIRPath expression for template interpolation."""
    return "{{" + expr + "}}"


def ctx_where(predicate: str) -> str:
    """Filter the current context with a predicate."""
    return f"%context.where({predicate})"


def res_context(path: str) -> str:
    """Navigate from %resource root."""
    return f"%resource.{path}"


def res_where(predicate: str) -> str:
    """Filter %resource with a predicate."""
    return f"%resource.where({predicate})"
