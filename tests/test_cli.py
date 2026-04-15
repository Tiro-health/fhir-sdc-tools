"""CLI integration tests using Click's CliRunner."""

from __future__ import annotations

import json
import os
import tempfile

from click.testing import CliRunner

from sdc.cli import cli
from sdc.composition import TEMPLATE_EXTRACT_PROFILE, TEMPLATE_EXTRACT_URL
from sdc.models import FHIR_VERSION_PROFILES, FhirVersion


def run(*args: str, input_json: str | None = None) -> dict:
    """Run a CLI command and return parsed JSON output."""
    runner = CliRunner()
    result = runner.invoke(cli, list(args), input=input_json)
    assert result.exit_code == 0, f"Command failed: {result.output}"
    return json.loads(result.output)


def run_raw(*args: str, input_json: str | None = None):
    """Run a CLI command and return the raw result."""
    runner = CliRunner()
    return runner.invoke(cli, list(args), input=input_json)


class TestInit:
    def test_basic_init(self) -> None:
        data = run("init", "--url", "http://example.org/q1", "--title", "Test")
        assert data["resourceType"] == "Questionnaire"
        assert data["url"] == "http://example.org/q1"
        assert data["title"] == "Test"
        assert data["status"] == "draft"

    def test_init_without_url(self) -> None:
        data = run("init", "--title", "No URL Form")
        assert data["resourceType"] == "Questionnaire"
        assert "url" not in data
        assert data["title"] == "No URL Form"
        assert data["status"] == "draft"

    def test_init_with_name(self) -> None:
        data = run(
            "init", "--url", "http://example.org/q1", "--title", "T", "--name", "test"
        )
        assert data["name"] == "test"

    def test_init_default_r5(self) -> None:
        data = run("init", "--url", "http://e.org", "--title", "T")
        assert FHIR_VERSION_PROFILES[FhirVersion.R5] in data["meta"]["profile"]

    def test_init_r5(self) -> None:
        data = run(
            "init", "--url", "http://e.org", "--title", "T", "--fhir-version", "R5"
        )
        assert FHIR_VERSION_PROFILES[FhirVersion.R5] in data["meta"]["profile"]

    def test_init_r5_case_insensitive(self) -> None:
        data = run(
            "init", "--url", "http://e.org", "--title", "T", "--fhir-version", "r5"
        )
        assert FHIR_VERSION_PROFILES[FhirVersion.R5] in data["meta"]["profile"]


class TestItemAdd:
    def test_add_item(self) -> None:
        init_json = json.dumps(run("init", "--url", "http://e.org", "--title", "T"))
        data = run(
            "item",
            "add",
            "--link-id",
            "1",
            "--text",
            "Name",
            "--type",
            "string",
            input_json=init_json,
        )
        assert len(data["item"]) == 1
        assert data["item"][0]["linkId"] == "1"

    def test_add_nested_item(self) -> None:
        init_json = json.dumps(run("init", "--url", "http://e.org", "--title", "T"))
        # Add a group
        q = run(
            "item",
            "add",
            "--link-id",
            "g1",
            "--text",
            "Group",
            "--type",
            "group",
            input_json=init_json,
        )
        # Add child
        q = run(
            "item",
            "add",
            "--link-id",
            "g1.1",
            "--text",
            "Child",
            "--type",
            "string",
            "--parent",
            "g1",
            input_json=json.dumps(q),
        )
        assert q["item"][0]["item"][0]["linkId"] == "g1.1"


class TestItemRemove:
    def test_remove_item(self) -> None:
        init_json = json.dumps(run("init", "--url", "http://e.org", "--title", "T"))
        q = run(
            "item",
            "add",
            "--link-id",
            "1",
            "--text",
            "Name",
            "--type",
            "string",
            input_json=init_json,
        )
        q = run("item", "remove", "--link-id", "1", input_json=json.dumps(q))
        assert "item" not in q or q.get("item") is None


class TestEnableWhen:
    def test_add_enable_when(self) -> None:
        init_json = json.dumps(run("init", "--url", "http://e.org", "--title", "T"))
        q = run(
            "item",
            "add",
            "--link-id",
            "1",
            "--text",
            "Q1",
            "--type",
            "boolean",
            input_json=init_json,
        )
        q = run(
            "item",
            "add",
            "--link-id",
            "2",
            "--text",
            "Q2",
            "--type",
            "string",
            input_json=json.dumps(q),
        )
        q = run(
            "enable-when",
            "add",
            "--link-id",
            "2",
            "--question",
            "1",
            "--operator",
            "=",
            "--answer-boolean",
            "true",
            input_json=json.dumps(q),
        )
        assert q["item"][1]["enableWhen"][0]["answerBoolean"] is True

    def test_set_behavior(self) -> None:
        init_json = json.dumps(run("init", "--url", "http://e.org", "--title", "T"))
        q = run(
            "item",
            "add",
            "--link-id",
            "1",
            "--text",
            "Q1",
            "--type",
            "string",
            input_json=init_json,
        )
        q = run(
            "enable-when",
            "set-behavior",
            "--link-id",
            "1",
            "--behavior",
            "all",
            input_json=json.dumps(q),
        )
        assert q["item"][0]["enableBehavior"] == "all"


class TestAnswerOption:
    def test_add_string_option(self) -> None:
        init_json = json.dumps(run("init", "--url", "http://e.org", "--title", "T"))
        q = run(
            "item",
            "add",
            "--link-id",
            "1",
            "--text",
            "Q1",
            "--type",
            "choice",
            input_json=init_json,
        )
        q = run(
            "answer-option",
            "add",
            "--link-id",
            "1",
            "--value-string",
            "Option A",
            input_json=json.dumps(q),
        )
        assert q["item"][0]["answerOption"][0]["valueString"] == "Option A"

    def test_add_coding_option(self) -> None:
        init_json = json.dumps(run("init", "--url", "http://e.org", "--title", "T"))
        q = run(
            "item",
            "add",
            "--link-id",
            "1",
            "--text",
            "Q1",
            "--type",
            "choice",
            input_json=init_json,
        )
        q = run(
            "answer-option",
            "add",
            "--link-id",
            "1",
            "--value-coding",
            "http://snomed.info/sct|123|Diabetes",
            input_json=json.dumps(q),
        )
        coding = q["item"][0]["answerOption"][0]["valueCoding"]
        assert coding["system"] == "http://snomed.info/sct"
        assert coding["code"] == "123"
        assert coding["display"] == "Diabetes"

    def test_set_value_set(self) -> None:
        init_json = json.dumps(run("init", "--url", "http://e.org", "--title", "T"))
        q = run(
            "item",
            "add",
            "--link-id",
            "1",
            "--text",
            "Q1",
            "--type",
            "choice",
            input_json=init_json,
        )
        q = run(
            "answer-option",
            "set-value-set",
            "--link-id",
            "1",
            "--url",
            "http://example.org/vs",
            input_json=json.dumps(q),
        )
        assert q["item"][0]["answerValueSet"] == "http://example.org/vs"


class TestExtension:
    def test_add_hidden(self) -> None:
        init_json = json.dumps(run("init", "--url", "http://e.org", "--title", "T"))
        q = run(
            "item", "add", "--link-id", "1", "--text", "Q1", "--type", "string",
            input_json=init_json,
        )
        q = run(
            "extension", "add", "hidden", "--link-id", "1",
            input_json=json.dumps(q),
        )
        ext = q["item"][0]["extension"][0]
        assert ext["url"] == "http://hl7.org/fhir/StructureDefinition/questionnaire-hidden"
        assert ext["valueBoolean"] is True

    def test_add_item_control(self) -> None:
        init_json = json.dumps(run("init", "--url", "http://e.org", "--title", "T"))
        q = run(
            "item", "add", "--link-id", "1", "--text", "Q1", "--type", "choice",
            input_json=init_json,
        )
        q = run(
            "extension", "add", "item-control", "--link-id", "1", "--code", "drop-down",
            input_json=json.dumps(q),
        )
        ext = q["item"][0]["extension"][0]
        assert ext["url"] == "http://hl7.org/fhir/StructureDefinition/questionnaire-itemControl"
        assert ext["valueCodeableConcept"]["coding"][0]["code"] == "drop-down"

    def test_add_calculated_expression(self) -> None:
        init_json = json.dumps(run("init", "--url", "http://e.org", "--title", "T"))
        q = run(
            "item", "add", "--link-id", "1", "--text", "BMI", "--type", "decimal",
            input_json=init_json,
        )
        q = run(
            "extension", "add", "calculated-expression",
            "--link-id", "1",
            "--expression", "%weight / %height.power(2)",
            input_json=json.dumps(q),
        )
        ext = q["item"][0]["extension"][0]
        assert ext["valueExpression"]["expression"] == "%weight / %height.power(2)"

    def test_add_variable(self) -> None:
        init_json = json.dumps(run("init", "--url", "http://e.org", "--title", "T"))
        q = run(
            "extension", "add", "variable",
            "--name", "weight",
            "--expression", "%resource.item.where(linkId='weight').answer.value",
            input_json=init_json,
        )
        assert len(q["extension"]) == 1
        ext = q["extension"][0]
        assert ext["url"] == "http://hl7.org/fhir/StructureDefinition/variable"
        assert ext["valueExpression"]["name"] == "weight"
        assert ext["valueExpression"]["expression"] == "%resource.item.where(linkId='weight').answer.value"

    def test_variable_with_description(self) -> None:
        init_json = json.dumps(run("init", "--url", "http://e.org", "--title", "T"))
        q = run(
            "extension", "add", "variable",
            "--name", "weight",
            "--expression", "%resource.item.where(linkId='weight').answer.value",
            "--description", "patient weight in kg",
            input_json=init_json,
        )
        ext = q["extension"][0]
        assert ext["valueExpression"]["name"] == "weight"
        assert ext["valueExpression"]["description"] == "patient weight in kg"

    def test_add_custom_by_url(self) -> None:
        init_json = json.dumps(run("init", "--url", "http://e.org", "--title", "T"))
        q = run(
            "extension", "add", "custom",
            "--url", "http://custom.org/ext",
            "--value-string", "hello",
            input_json=init_json,
        )
        assert q["extension"][0]["url"] == "http://custom.org/ext"
        assert q["extension"][0]["valueString"] == "hello"

    def test_remove_by_name(self) -> None:
        init_json = json.dumps(run("init", "--url", "http://e.org", "--title", "T"))
        q = run(
            "extension", "add", "variable",
            "--name", "w",
            "--expression", "test",
            input_json=init_json,
        )
        q = run(
            "extension", "remove", "variable",
            input_json=json.dumps(q),
        )
        assert "extension" not in q or q.get("extension") is None

    def test_remove_by_url(self) -> None:
        init_json = json.dumps(run("init", "--url", "http://e.org", "--title", "T"))
        q = run(
            "extension", "add", "custom",
            "--url", "http://custom.org/ext",
            "--value-string", "hello",
            input_json=init_json,
        )
        q = run(
            "extension", "remove",
            "--url", "http://custom.org/ext",
            input_json=json.dumps(q),
        )
        assert "extension" not in q or q.get("extension") is None


class TestMeta:
    def test_set_meta_fields(self) -> None:
        init_json = json.dumps(run("init", "--url", "http://e.org", "--title", "T"))
        q = run(
            "meta",
            "--status",
            "active",
            "--publisher",
            "My Org",
            input_json=init_json,
        )
        assert q["status"] == "active"
        assert q["publisher"] == "My Org"


class TestValidate:
    def test_valid_passes_through(self) -> None:
        init_json = json.dumps(run("init", "--url", "http://e.org", "--title", "T"))
        q = run(
            "item",
            "add",
            "--link-id",
            "1",
            "--text",
            "Q1",
            "--type",
            "string",
            input_json=init_json,
        )
        result = run_raw("validate", input_json=json.dumps(q))
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["resourceType"] == "Questionnaire"

    def test_warnings_to_stderr(self) -> None:
        init_json = json.dumps(run("init", "--url", "http://e.org", "--title", "T"))
        # No items => warning
        result = run_raw("validate", input_json=init_json)
        assert result.exit_code == 0
        # Output still contains valid JSON (stderr warnings are separate in real usage)


class TestPipeChain:
    def test_full_pipe(self) -> None:
        """Simulate a full pipe chain by chaining outputs."""
        q = run(
            "init",
            "--url",
            "http://example.org/diabetes",
            "--title",
            "Diabetes Screening",
        )
        q = run(
            "item",
            "add",
            "--link-id",
            "1",
            "--text",
            "Has diabetes?",
            "--type",
            "boolean",
            input_json=json.dumps(q),
        )
        q = run(
            "item",
            "add",
            "--link-id",
            "2",
            "--text",
            "Type?",
            "--type",
            "choice",
            input_json=json.dumps(q),
        )
        q = run(
            "enable-when",
            "add",
            "--link-id",
            "2",
            "--question",
            "1",
            "--operator",
            "=",
            "--answer-boolean",
            "true",
            input_json=json.dumps(q),
        )
        q = run(
            "answer-option",
            "add",
            "--link-id",
            "2",
            "--value-string",
            "Type 1",
            input_json=json.dumps(q),
        )
        q = run(
            "answer-option",
            "add",
            "--link-id",
            "2",
            "--value-string",
            "Type 2",
            input_json=json.dumps(q),
        )
        q = run(
            "extension",
            "add",
            "item-control",
            "--link-id",
            "2",
            "--code",
            "drop-down",
            input_json=json.dumps(q),
        )

        # Verify final structure
        assert q["resourceType"] == "Questionnaire"
        assert q["title"] == "Diabetes Screening"
        assert len(q["item"]) == 2
        assert q["item"][0]["type"] == "boolean"
        assert q["item"][1]["enableWhen"][0]["answerBoolean"] is True
        assert len(q["item"][1]["answerOption"]) == 2
        assert (
            q["item"][1]["extension"][0]["valueCodeableConcept"]["coding"][0]["code"]
            == "drop-down"
        )


class TestTranslate:
    def test_translate_item_text(self) -> None:
        init_json = json.dumps(run("init", "--url", "http://e.org", "--title", "T"))
        q = run(
            "item",
            "add",
            "--link-id",
            "1",
            "--text",
            "Name",
            "--type",
            "string",
            input_json=init_json,
        )
        q = run(
            "translate",
            "--link-id",
            "1",
            "--lang",
            "nl",
            "--value",
            "Naam",
            input_json=json.dumps(q),
        )
        assert "_text" in q["item"][0]
        exts = q["item"][0]["_text"]["extension"]
        assert len(exts) == 1
        assert exts[0]["extension"][0]["valueCode"] == "nl"
        assert exts[0]["extension"][1]["valueString"] == "Naam"

    def test_translate_title(self) -> None:
        init_json = json.dumps(run("init", "--url", "http://e.org", "--title", "T"))
        q = run(
            "translate",
            "--field",
            "title",
            "--lang",
            "nl",
            "--value",
            "Inname",
            input_json=init_json,
        )
        assert "_title" in q
        assert len(q["_title"]["extension"]) == 1

    def test_translate_multiple_languages(self) -> None:
        init_json = json.dumps(run("init", "--url", "http://e.org", "--title", "T"))
        q = run(
            "item",
            "add",
            "--link-id",
            "1",
            "--text",
            "Name",
            "--type",
            "string",
            input_json=init_json,
        )
        q = run(
            "translate",
            "--link-id",
            "1",
            "--lang",
            "nl",
            "--value",
            "Naam",
            input_json=json.dumps(q),
        )
        q = run(
            "translate",
            "--link-id",
            "1",
            "--lang",
            "fr",
            "--value",
            "Nom",
            input_json=json.dumps(q),
        )
        exts = q["item"][0]["_text"]["extension"]
        assert len(exts) == 2

    def test_translate_answer_by_code(self) -> None:
        init_json = json.dumps(run("init", "--url", "http://e.org", "--title", "T"))
        q = run(
            "item",
            "add",
            "--link-id",
            "1",
            "--text",
            "Gender",
            "--type",
            "choice",
            input_json=init_json,
        )
        q = run(
            "answer-option",
            "add",
            "--link-id",
            "1",
            "--value-coding",
            "http://hl7.org/fhir/administrative-gender|male|Male",
            input_json=json.dumps(q),
        )
        q = run(
            "translate",
            "--link-id",
            "1",
            "--answer-code",
            "male",
            "--lang",
            "nl",
            "--value",
            "Man",
            input_json=json.dumps(q),
        )
        coding = q["item"][0]["answerOption"][0]["valueCoding"]
        assert "_display" in coding
        assert (
            coding["_display"]["extension"][0]["extension"][1]["valueString"] == "Man"
        )

    def test_translate_answer_by_index(self) -> None:
        init_json = json.dumps(run("init", "--url", "http://e.org", "--title", "T"))
        q = run(
            "item",
            "add",
            "--link-id",
            "1",
            "--text",
            "Pick",
            "--type",
            "choice",
            input_json=init_json,
        )
        q = run(
            "answer-option",
            "add",
            "--link-id",
            "1",
            "--value-string",
            "Option A",
            input_json=json.dumps(q),
        )
        q = run(
            "translate",
            "--link-id",
            "1",
            "--answer-index",
            "0",
            "--lang",
            "nl",
            "--value",
            "Optie A",
            input_json=json.dumps(q),
        )
        opt = q["item"][0]["answerOption"][0]
        assert "_valueString" in opt

    def test_error_no_target(self) -> None:
        init_json = json.dumps(run("init", "--url", "http://e.org", "--title", "T"))
        result = run_raw(
            "translate",
            "--lang",
            "nl",
            "--value",
            "test",
            input_json=init_json,
        )
        assert result.exit_code != 0

    def test_error_both_targets(self) -> None:
        init_json = json.dumps(run("init", "--url", "http://e.org", "--title", "T"))
        result = run_raw(
            "translate",
            "--link-id",
            "1",
            "--field",
            "title",
            "--lang",
            "nl",
            "--value",
            "test",
            input_json=init_json,
        )
        assert result.exit_code != 0


def _write_composition_file(path: str) -> None:
    """Write a minimal Composition JSON to a temp file."""
    comp = {
        "resourceType": "Composition",
        "id": "comp-1",
        "status": "final",
        "type": {"coding": [{"system": "http://loinc.org", "code": "11488-4"}]},
        "title": "Test Report",
        "section": [
            {
                "title": "Findings",
                "text": {
                    "status": "generated",
                    "div": '<div xmlns="http://www.w3.org/1999/xhtml">content</div>',
                },
            }
        ],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(comp, f)


class TestTemplateEmbed:
    def test_embed_from_file(self) -> None:
        init_json = json.dumps(run("init", "--url", "http://e.org", "--title", "T"))
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as tmp:
            tmp_path = tmp.name
        try:
            _write_composition_file(tmp_path)
            q = run(
                "template", "embed", "--file", tmp_path,
                input_json=init_json,
            )
            # contained resource
            assert "contained" in q
            assert q["contained"][0]["resourceType"] == "Composition"
            assert q["contained"][0]["id"] == "comp-1"
            # templateExtract extension
            ext_urls = [e["url"] for e in q["extension"]]
            assert TEMPLATE_EXTRACT_URL in ext_urls
            # profile
            assert TEMPLATE_EXTRACT_PROFILE in q["meta"]["profile"]
        finally:
            os.unlink(tmp_path)

    def test_embed_missing_file(self) -> None:
        init_json = json.dumps(run("init", "--url", "http://e.org", "--title", "T"))
        result = run_raw(
            "template", "embed", "--file", "/nonexistent/path.json",
            input_json=init_json,
        )
        assert result.exit_code != 0

    def test_embed_pipe_chain(self) -> None:
        """Full pipe: init -> item add -> template embed -> validate."""
        q = run("init", "--url", "http://example.org/q1", "--title", "Report")
        q = run(
            "item", "add", "--link-id", "1", "--text", "Q1", "--type", "string",
            input_json=json.dumps(q),
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as tmp:
            tmp_path = tmp.name
        try:
            _write_composition_file(tmp_path)
            q = run(
                "template", "embed", "--file", tmp_path,
                input_json=json.dumps(q),
            )
            # Validate still passes
            result = run_raw("validate", input_json=json.dumps(q))
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["resourceType"] == "Questionnaire"
            assert "contained" in data
            assert len(data["item"]) == 1
        finally:
            os.unlink(tmp_path)


# --- Composition CLI ---


class TestCompositionInit:
    def test_basic(self) -> None:
        c = run(
            "composition", "init",
            "--id", "report",
            "--title", "Report",
            "--type-system", "http://loinc.org",
            "--type-code", "11488-4",
        )
        assert c["resourceType"] == "Composition"
        assert c["id"] == "report"
        assert c["title"] == "Report"
        assert c["status"] == "final"
        assert c["type"]["coding"][0]["system"] == "http://loinc.org"
        assert c["type"]["coding"][0]["code"] == "11488-4"

    def test_with_display(self) -> None:
        c = run(
            "composition", "init",
            "--id", "r", "--title", "R",
            "--type-system", "http://loinc.org", "--type-code", "11488-4",
            "--type-display", "Consultation note",
        )
        assert c["type"]["coding"][0]["display"] == "Consultation note"

    def test_custom_status(self) -> None:
        c = run(
            "composition", "init",
            "--id", "r", "--title", "R",
            "--type-system", "http://loinc.org", "--type-code", "11488-4",
            "--status", "preliminary",
        )
        assert c["status"] == "preliminary"


def _init_composition() -> str:
    """Return JSON string of a minimal Composition."""
    c = run(
        "composition", "init",
        "--id", "report", "--title", "Report",
        "--type-system", "http://loinc.org", "--type-code", "11488-4",
    )
    return json.dumps(c)


class TestCompositionSectionAdd:
    def test_root_section(self) -> None:
        c = run(
            "composition", "section", "add",
            "--title", "Findings",
            "--context", "%resource.item.where(linkId='findings')",
            "--text", "<p>Content</p>",
            input_json=_init_composition(),
        )
        assert len(c["section"]) == 1
        assert c["section"][0]["title"] == "Findings"
        assert "Content" in c["section"][0]["text"]["div"]

    def test_nested_section(self) -> None:
        comp_json = _init_composition()
        c = run(
            "composition", "section", "add",
            "--title", "Parent",
            input_json=comp_json,
        )
        c = run(
            "composition", "section", "add",
            "--title", "Child",
            "--parent", "Parent",
            "--text", "<p>nested</p>",
            input_json=json.dumps(c),
        )
        assert len(c["section"]) == 1
        assert len(c["section"][0]["section"]) == 1
        assert c["section"][0]["section"][0]["title"] == "Child"

    def test_with_text_file(self) -> None:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".html", delete=False, encoding="utf-8"
        ) as f:
            f.write("<p>from file</p>")
            tmp_path = f.name
        try:
            c = run(
                "composition", "section", "add",
                "--title", "FromFile",
                "--text-file", tmp_path,
                input_json=_init_composition(),
            )
            assert "from file" in c["section"][0]["text"]["div"]
        finally:
            os.unlink(tmp_path)

    def test_duplicate_title_error(self) -> None:
        comp_json = _init_composition()
        c = run(
            "composition", "section", "add",
            "--title", "A",
            input_json=comp_json,
        )
        result = run_raw(
            "composition", "section", "add",
            "--title", "A",
            input_json=json.dumps(c),
        )
        assert result.exit_code != 0


class TestCompositionSectionSetContext:
    def test_set(self) -> None:
        comp_json = _init_composition()
        c = run(
            "composition", "section", "add",
            "--title", "A",
            input_json=comp_json,
        )
        c = run(
            "composition", "section", "set-context",
            "--title", "A",
            "--context", "%resource.item.where(linkId='q1')",
            input_json=json.dumps(c),
        )
        ext = c["section"][0]["extension"][0]
        assert ext["valueString"] == "%resource.item.where(linkId='q1')"


class TestCompositionSectionSetText:
    def test_set(self) -> None:
        comp_json = _init_composition()
        c = run(
            "composition", "section", "add",
            "--title", "A",
            input_json=comp_json,
        )
        c = run(
            "composition", "section", "set-text",
            "--title", "A",
            "--text", "<p>updated</p>",
            input_json=json.dumps(c),
        )
        assert "updated" in c["section"][0]["text"]["div"]


class TestCompositionPipeChain:
    def test_full_pipeline(self) -> None:
        """Build a small Composition via pipe chain and verify structure."""
        c = run(
            "composition", "init",
            "--id", "report", "--title", "Colonoscopy",
            "--type-system", "http://loinc.org", "--type-code", "11488-4",
        )
        c = run(
            "composition", "section", "add",
            "--title", "Procedure",
            "--context", "%resource.item.where(linkId='group')",
            "--text", "<p>Date: {{%context.item.where(linkId='datum').answer.value}}</p>",
            input_json=json.dumps(c),
        )
        c = run(
            "composition", "section", "add",
            "--title", "Findings",
            "--context", "%resource.item.where(linkId='findings')",
            "--text", "<!-- sections -->",
            input_json=json.dumps(c),
        )
        c = run(
            "composition", "section", "add",
            "--title", "Polyps",
            "--parent", "Findings",
            "--context", "%context.item.where(linkId='polyp')",
            "--text", "<p>Location: {{%context.item.where(linkId='locatie').answer.value.display}}</p>",
            input_json=json.dumps(c),
        )
        # Verify structure
        assert c["resourceType"] == "Composition"
        assert c["id"] == "report"
        assert len(c["section"]) == 2
        assert c["section"][0]["title"] == "Procedure"
        assert c["section"][1]["title"] == "Findings"
        # Nested polyp section
        findings = c["section"][1]
        assert len(findings["section"]) == 1
        assert findings["section"][0]["title"] == "Polyps"
        # Context extensions present
        assert findings["section"][0]["extension"][0]["valueString"].startswith("%context")


class TestPipeChainSubprocess:
    """Test pipe chaining with real subprocesses (not CliRunner) to catch
    buffering, SIGPIPE, and broken-pipe issues that only manifest in real
    shell pipelines."""

    def test_many_variable_extensions_via_subprocess(self) -> None:
        """Reproduce issue #26: pipe breaks after ~8-10 chained 'sdc extension
        add variable' commands when reading from cat."""
        import subprocess

        # Build a non-trivial base questionnaire (20+ items)
        init_json = json.dumps(
            run("init", "--url", "http://example.org/q1", "--title", "Pipe Test")
        )
        q = json.loads(init_json)
        for i in range(1, 21):
            q = run(
                "item", "add",
                "--link-id", f"item-{i}",
                "--text", f"Question {i} with some extra text to increase size",
                "--type", "string",
                input_json=json.dumps(q),
            )
        base_json = json.dumps(q)

        # Build a shell pipeline: echo JSON | sdc ext add var ... | ... (12 stages)
        NUM_VARS = 12
        pipeline = "cat"
        for i in range(1, NUM_VARS + 1):
            pipeline += (
                f" | sdc extension add variable"
                f" --name var{i}"
                f" --expression \"%resource.item.where(linkId='item-{i}').answer.value\""
            )

        result = subprocess.run(
            pipeline,
            shell=True,
            input=base_json.encode("utf-8"),
            capture_output=True,
            timeout=60,
        )
        assert result.returncode == 0, (
            f"Pipeline failed (exit {result.returncode}).\n"
            f"stderr: {result.stderr.decode('utf-8', errors='replace')}"
        )

        data = json.loads(result.stdout)
        assert data["resourceType"] == "Questionnaire"

        # All 12 new variables should be present
        var_names = [
            ext["valueExpression"]["name"]
            for ext in data.get("extension", [])
            if "valueExpression" in ext and "name" in ext.get("valueExpression", {})
        ]
        for i in range(1, NUM_VARS + 1):
            assert f"var{i}" in var_names, f"var{i} missing from output"

    def test_empty_stdin_gives_clear_error(self) -> None:
        """When stdin is empty (upstream failed), error message should be
        helpful, not a raw JSONDecodeError."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["extension", "add", "variable", "--name", "x", "--expression", "1"],
            input="",
        )
        assert result.exit_code != 0
        assert "Empty input on stdin" in result.output or "Empty input on stdin" in str(
            result.exception
        )
