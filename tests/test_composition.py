"""Tests for Composition models and section builder."""

from __future__ import annotations

import json

from sdc.composition import (
    TEMPLATE_EXTRACT_CONTEXT_URL,
    Composition,
    CompositionSection,
    Narrative,
    section,
)


class TestNarrative:
    def test_default_status(self) -> None:
        n = Narrative(div="<div>hello</div>")
        assert n.status == "generated"

    def test_roundtrip(self) -> None:
        n = Narrative(div='<div xmlns="http://www.w3.org/1999/xhtml">text</div>')
        data = json.loads(n.model_dump_json(exclude_none=True))
        assert data["status"] == "generated"
        assert "text" in data["div"]


class TestCompositionSection:
    def test_minimal(self) -> None:
        s = CompositionSection(title="Section A")
        data = json.loads(s.model_dump_json(by_alias=True, exclude_none=True))
        assert data["title"] == "Section A"
        assert "extension" not in data
        assert "section" not in data

    def test_nested_sections(self) -> None:
        child = CompositionSection(title="Child")
        parent = CompositionSection(title="Parent", section=[child])
        data = json.loads(parent.model_dump_json(by_alias=True, exclude_none=True))
        assert len(data["section"]) == 1
        assert data["section"][0]["title"] == "Child"


class TestComposition:
    def test_minimal_roundtrip(self) -> None:
        c = Composition(
            id="comp-1",
            type={"coding": [{"system": "http://loinc.org", "code": "11488-4"}]},
            title="Test Composition",
        )
        data = json.loads(c.model_dump_json(by_alias=True, exclude_none=True))
        assert data["resourceType"] == "Composition"
        assert data["id"] == "comp-1"
        assert data["status"] == "final"
        assert data["type"]["coding"][0]["code"] == "11488-4"
        assert data["title"] == "Test Composition"

    def test_extra_fields_preserved(self) -> None:
        raw = {
            "resourceType": "Composition",
            "id": "comp-1",
            "status": "final",
            "type": {"coding": [{"system": "http://loinc.org", "code": "11488-4"}]},
            "subject": {"reference": "Patient/123"},
        }
        c = Composition.model_validate(raw)
        data = json.loads(c.model_dump_json(by_alias=True, exclude_none=True))
        assert data["subject"]["reference"] == "Patient/123"


class TestSection:
    def test_minimal_section(self) -> None:
        s = section(text="Hello")
        assert s.text is not None
        assert 'xmlns="http://www.w3.org/1999/xhtml"' in s.text.div
        assert "Hello" in s.text.div
        assert s.extension is None
        assert s.title is None
        assert s.section is None

    def test_section_with_context(self) -> None:
        s = section(
            title="Findings",
            context="%resource.item.where(linkId='findings')",
        )
        assert s.title == "Findings"
        assert s.extension is not None
        assert len(s.extension) == 1
        assert s.extension[0].url == TEMPLATE_EXTRACT_CONTEXT_URL

    def test_section_with_children(self) -> None:
        child = section(text="child content")
        parent = section(title="Parent", children=[child])
        assert parent.section is not None
        assert len(parent.section) == 1
        assert parent.section[0].text.div is not None

    def test_narrative_wrapping(self) -> None:
        s = section(text="<p>paragraph</p>")
        assert s.text.div == (
            '<div xmlns="http://www.w3.org/1999/xhtml"><p>paragraph</p></div>'
        )

    def test_empty_text_not_set(self) -> None:
        s = section(title="Empty")
        assert s.text is None

    def test_all_options(self) -> None:
        child = section(text="nested")
        s = section(
            title="Full",
            context="%resource.item.where(linkId='q1')",
            text="content",
            children=[child],
        )
        assert s.title == "Full"
        assert s.extension is not None
        assert s.text is not None
        assert s.section is not None
        assert len(s.section) == 1
