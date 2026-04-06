"""Tests for Pydantic models: roundtrip serialization and extra field preservation."""

from __future__ import annotations

import json

from sdc.models import (
    FHIR_VERSION_PROFILES,
    EnableWhen,
    Extension,
    FhirVersion,
    PublicationStatus,
    Questionnaire,
    QuestionnaireItem,
    QuestionnaireItemType,
    resolve_fhir_version,
    set_fhir_version,
)


class TestQuestionnaire:
    def test_minimal_roundtrip(self) -> None:
        q = Questionnaire(url="http://example.org/q1", title="Test")
        data = json.loads(q.model_dump_json(by_alias=True, exclude_none=True))
        assert data["resourceType"] == "Questionnaire"
        assert data["url"] == "http://example.org/q1"
        assert data["title"] == "Test"
        assert data["status"] == "draft"
        assert "item" not in data

    def test_extra_fields_preserved(self) -> None:
        raw = {
            "resourceType": "Questionnaire",
            "url": "http://example.org/q1",
            "status": "draft",
            "meta": {"versionId": "1"},
            "language": "en",
        }
        q = Questionnaire.model_validate(raw)
        data = json.loads(q.model_dump_json(by_alias=True, exclude_none=True))
        assert data["meta"]["versionId"] == "1"
        assert data["language"] == "en"

    def test_default_status_is_draft(self) -> None:
        q = Questionnaire(url="http://example.org/q1")
        assert q.status == PublicationStatus.DRAFT

    def test_populate_by_name(self) -> None:
        q = Questionnaire(resource_type="Questionnaire", url="http://example.org/q1")
        assert q.resource_type == "Questionnaire"


class TestQuestionnaireItem:
    def test_basic_item_roundtrip(self) -> None:
        item = QuestionnaireItem(
            link_id="1", text="Name", type=QuestionnaireItemType.STRING
        )
        data = json.loads(item.model_dump_json(by_alias=True, exclude_none=True))
        assert data["linkId"] == "1"
        assert data["text"] == "Name"
        assert data["type"] == "string"

    def test_nested_items(self) -> None:
        group = QuestionnaireItem(
            link_id="g1",
            text="Group",
            type=QuestionnaireItemType.GROUP,
            item=[
                QuestionnaireItem(
                    link_id="g1.1", text="Child", type=QuestionnaireItemType.BOOLEAN
                )
            ],
        )
        data = json.loads(group.model_dump_json(by_alias=True, exclude_none=True))
        assert len(data["item"]) == 1
        assert data["item"][0]["linkId"] == "g1.1"

    def test_extra_fields_on_item(self) -> None:
        raw = {
            "linkId": "1",
            "type": "string",
            "definition": "http://example.org/def",
            "code": [{"system": "http://loinc.org", "code": "12345-6"}],
        }
        item = QuestionnaireItem.model_validate(raw)
        data = json.loads(item.model_dump_json(by_alias=True, exclude_none=True))
        assert data["definition"] == "http://example.org/def"
        assert data["code"][0]["code"] == "12345-6"

    def test_from_alias(self) -> None:
        raw = {"linkId": "1", "type": "boolean", "readOnly": True}
        item = QuestionnaireItem.model_validate(raw)
        assert item.read_only is True


class TestEnableWhen:
    def test_with_answer_via_extra(self) -> None:
        raw = {"question": "1", "operator": "=", "answerBoolean": True}
        ew = EnableWhen.model_validate(raw)
        data = json.loads(ew.model_dump_json(by_alias=True, exclude_none=True))
        assert data["answerBoolean"] is True
        assert data["operator"] == "="


class TestExtension:
    def test_simple_extension(self) -> None:
        ext = Extension.model_validate(
            {
                "url": "http://hl7.org/fhir/StructureDefinition/questionnaire-hidden",
                "valueBoolean": True,
            }
        )
        data = json.loads(ext.model_dump_json(by_alias=True, exclude_none=True))
        assert data["valueBoolean"] is True

    def test_expression_extension(self) -> None:
        ext = Extension.model_validate(
            {
                "url": "http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire-calculatedExpression",
                "valueExpression": {
                    "language": "text/fhirpath",
                    "expression": "%weight / %height.power(2)",
                },
            }
        )
        data = json.loads(ext.model_dump_json(by_alias=True, exclude_none=True))
        assert data["valueExpression"]["language"] == "text/fhirpath"


class TestFhirVersion:
    def test_set_fhir_version_r4(self) -> None:
        q = Questionnaire(url="http://example.org/q1")
        q = set_fhir_version(q, FhirVersion.R4)
        assert q.fhir_version == FhirVersion.R4
        data = json.loads(q.model_dump_json(by_alias=True, exclude_none=True))
        assert FHIR_VERSION_PROFILES[FhirVersion.R4] in data["meta"]["profile"]

    def test_set_fhir_version_r5(self) -> None:
        q = Questionnaire(url="http://example.org/q1")
        q = set_fhir_version(q, FhirVersion.R5)
        assert q.fhir_version == FhirVersion.R5

    def test_detect_version_from_profile(self) -> None:
        raw = {
            "resourceType": "Questionnaire",
            "meta": {
                "profile": ["http://hl7.org/fhir/5.0/StructureDefinition/Questionnaire"]
            },
        }
        q = Questionnaire.model_validate(raw)
        assert q.fhir_version == FhirVersion.R5

    def test_no_version_returns_none(self) -> None:
        q = Questionnaire(url="http://example.org/q1")
        assert q.fhir_version is None

    def test_resolve_fhir_version_from_questionnaire(self) -> None:
        q = Questionnaire(url="http://example.org/q1")
        q = set_fhir_version(q, FhirVersion.R5)
        assert resolve_fhir_version(q) == FhirVersion.R5

    def test_resolve_fhir_version_from_env(self, monkeypatch: object) -> None:
        monkeypatch.setenv("SDC_FHIR_VERSION", "R5")  # type: ignore[attr-defined]
        assert resolve_fhir_version() == FhirVersion.R5

    def test_resolve_fhir_version_default_r4(self) -> None:
        # No profile, no env var => R4
        q = Questionnaire(url="http://example.org/q1")
        assert resolve_fhir_version(q) == FhirVersion.R4

    def test_set_version_preserves_other_profiles(self) -> None:
        raw = {
            "resourceType": "Questionnaire",
            "meta": {
                "profile": [
                    "http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire"
                ]
            },
        }
        q = Questionnaire.model_validate(raw)
        q = set_fhir_version(q, FhirVersion.R4)
        assert len(q.meta.profile) == 2
        assert (
            "http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire"
            in q.meta.profile
        )

    def test_set_version_replaces_existing_version(self) -> None:
        q = Questionnaire(url="http://example.org/q1")
        q = set_fhir_version(q, FhirVersion.R4)
        q = set_fhir_version(q, FhirVersion.R5)
        assert q.fhir_version == FhirVersion.R5
        # Should not have both version profiles
        version_profiles = [
            p for p in q.meta.profile if p in FHIR_VERSION_PROFILES.values()
        ]
        assert len(version_profiles) == 1

    def test_r5_item_types(self) -> None:
        """R5-only types should parse fine."""
        item = QuestionnaireItem(
            link_id="1", text="Code", type=QuestionnaireItemType.CODING
        )
        assert item.type == QuestionnaireItemType.CODING

    def test_meta_extra_fields_preserved(self) -> None:
        """Meta extra fields like versionId survive version setting."""
        raw = {
            "resourceType": "Questionnaire",
            "meta": {"versionId": "3", "lastUpdated": "2024-01-01T00:00:00Z"},
        }
        q = Questionnaire.model_validate(raw)
        q = set_fhir_version(q, FhirVersion.R4)
        data = json.loads(q.model_dump_json(by_alias=True, exclude_none=True))
        assert data["meta"]["versionId"] == "3"
        assert data["meta"]["lastUpdated"] == "2024-01-01T00:00:00Z"
