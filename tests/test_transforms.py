"""Tests for pure transform functions."""

from __future__ import annotations

import pytest

from sdc.models import (
    TRANSLATION_URL,
    EnableWhen,
    EnableWhenOperator,
    Extension,
    FhirVersion,
    Questionnaire,
    QuestionnaireItem,
    QuestionnaireItemType,
    set_fhir_version,
)
from sdc.transforms import (
    add_answer_option,
    add_enable_when,
    add_extension,
    add_item,
    add_translation,
    find_item,
    remove_extension,
    remove_item,
    set_answer_value_set,
    set_enable_behavior,
    set_meta,
    validate,
)


class TestFindItem:
    def test_find_top_level(self, questionnaire_with_items: Questionnaire) -> None:
        item = find_item(questionnaire_with_items.item, "1")
        assert item is not None
        assert item.link_id == "1"

    def test_find_nested(self, questionnaire_with_items: Questionnaire) -> None:
        item = find_item(questionnaire_with_items.item, "2.1")
        assert item is not None
        assert item.text == "Age"

    def test_not_found(self, questionnaire_with_items: Questionnaire) -> None:
        item = find_item(questionnaire_with_items.item, "999")
        assert item is None


class TestAddItem:
    def test_add_to_empty(self, empty_questionnaire: Questionnaire) -> None:
        new = QuestionnaireItem(
            link_id="1", text="Name", type=QuestionnaireItemType.STRING
        )
        result = add_item(empty_questionnaire, new)
        assert len(result.item) == 1
        assert result.item[0].link_id == "1"

    def test_add_to_existing(self, questionnaire_with_items: Questionnaire) -> None:
        new = QuestionnaireItem(
            link_id="3", text="Email", type=QuestionnaireItemType.STRING
        )
        result = add_item(questionnaire_with_items, new)
        assert len(result.item) == 3

    def test_add_nested(self, questionnaire_with_items: Questionnaire) -> None:
        new = QuestionnaireItem(
            link_id="2.2", text="Height", type=QuestionnaireItemType.DECIMAL
        )
        result = add_item(questionnaire_with_items, new, parent_link_id="2")
        parent = find_item(result.item, "2")
        assert len(parent.item) == 2
        assert parent.item[1].link_id == "2.2"

    def test_add_nested_parent_not_found(
        self, empty_questionnaire: Questionnaire
    ) -> None:
        new = QuestionnaireItem(
            link_id="1.1", text="X", type=QuestionnaireItemType.STRING
        )
        with pytest.raises(ValueError, match="Parent item '999' not found"):
            add_item(empty_questionnaire, new, parent_link_id="999")

    def test_original_not_mutated(self, empty_questionnaire: Questionnaire) -> None:
        new = QuestionnaireItem(
            link_id="1", text="Name", type=QuestionnaireItemType.STRING
        )
        add_item(empty_questionnaire, new)
        assert empty_questionnaire.item is None


class TestRemoveItem:
    def test_remove_top_level(self, questionnaire_with_items: Questionnaire) -> None:
        result = remove_item(questionnaire_with_items, "1")
        assert len(result.item) == 1
        assert result.item[0].link_id == "2"

    def test_remove_nested(self, questionnaire_with_items: Questionnaire) -> None:
        result = remove_item(questionnaire_with_items, "2.1")
        group = find_item(result.item, "2")
        assert group.item is None or len(group.item) == 0

    def test_remove_from_empty(self, empty_questionnaire: Questionnaire) -> None:
        with pytest.raises(ValueError, match="not found"):
            remove_item(empty_questionnaire, "1")


class TestAddEnableWhen:
    def test_add_enable_when(self, questionnaire_with_items: Questionnaire) -> None:
        ew = EnableWhen.model_validate(
            {"question": "1", "operator": "=", "answerBoolean": True}
        )
        result = add_enable_when(questionnaire_with_items, "2.1", ew)
        item = find_item(result.item, "2.1")
        assert len(item.enable_when) == 1
        assert item.enable_when[0].question == "1"

    def test_item_not_found(self, empty_questionnaire: Questionnaire) -> None:
        ew = EnableWhen(question="1", operator=EnableWhenOperator.EQUALS)
        with pytest.raises(ValueError, match="not found"):
            add_enable_when(empty_questionnaire, "999", ew)


class TestSetEnableBehavior:
    def test_set_behavior(self, questionnaire_with_items: Questionnaire) -> None:
        result = set_enable_behavior(questionnaire_with_items, "2.1", "all")
        item = find_item(result.item, "2.1")
        assert item.enable_behavior == "all"


class TestAddAnswerOption:
    def test_add_option(self, questionnaire_with_items: Questionnaire) -> None:
        result = add_answer_option(
            questionnaire_with_items, "1", {"valueString": "Option A"}
        )
        item = find_item(result.item, "1")
        assert len(item.answer_option) == 1
        assert item.answer_option[0]["valueString"] == "Option A"


class TestSetAnswerValueSet:
    def test_set_value_set(self, questionnaire_with_items: Questionnaire) -> None:
        result = set_answer_value_set(
            questionnaire_with_items, "1", "http://example.org/vs"
        )
        item = find_item(result.item, "1")
        assert item.answer_value_set == "http://example.org/vs"


class TestAddExtension:
    def test_add_to_questionnaire_level(
        self, empty_questionnaire: Questionnaire
    ) -> None:
        ext = Extension.model_validate(
            {"url": "http://example.org/ext", "valueString": "test"}
        )
        result = add_extension(empty_questionnaire, ext)
        assert len(result.extension) == 1
        assert result.extension[0].url == "http://example.org/ext"

    def test_add_to_item(self, questionnaire_with_items: Questionnaire) -> None:
        ext = Extension.model_validate(
            {
                "url": "http://hl7.org/fhir/StructureDefinition/questionnaire-hidden",
                "valueBoolean": True,
            }
        )
        result = add_extension(questionnaire_with_items, ext, "1")
        item = find_item(result.item, "1")
        assert len(item.extension) == 1


class TestRemoveExtension:
    def test_remove_from_questionnaire(self) -> None:
        q = Questionnaire(
            url="http://example.org/q1",
            extension=[
                Extension.model_validate(
                    {"url": "http://example.org/ext", "valueString": "test"}
                )
            ],
        )
        result = remove_extension(q, "http://example.org/ext")
        assert result.extension is None


class TestSetMeta:
    def test_set_fields(self, empty_questionnaire: Questionnaire) -> None:
        result = set_meta(empty_questionnaire, publisher="My Org", description="A form")
        assert result.publisher == "My Org"
        assert result.description == "A form"


class TestValidate:
    def test_no_items_warning(self, empty_questionnaire: Questionnaire) -> None:
        warnings = validate(empty_questionnaire)
        assert any("no items" in w for w in warnings)

    def test_duplicate_link_ids(self) -> None:
        q = Questionnaire(
            url="http://example.org/q1",
            item=[
                QuestionnaireItem(
                    link_id="1", text="A", type=QuestionnaireItemType.STRING
                ),
                QuestionnaireItem(
                    link_id="1", text="B", type=QuestionnaireItemType.STRING
                ),
            ],
        )
        warnings = validate(q)
        assert any("Duplicate linkId" in w for w in warnings)

    def test_enable_when_bad_ref(self) -> None:
        q = Questionnaire(
            url="http://example.org/q1",
            item=[
                QuestionnaireItem(
                    link_id="1",
                    text="A",
                    type=QuestionnaireItemType.STRING,
                    enable_when=[
                        EnableWhen.model_validate(
                            {"question": "999", "operator": "=", "answerBoolean": True}
                        )
                    ],
                ),
            ],
        )
        warnings = validate(q)
        assert any("unknown linkId '999'" in w for w in warnings)

    def test_valid_questionnaire(self, questionnaire_with_items: Questionnaire) -> None:
        warnings = validate(questionnaire_with_items)
        assert warnings == []

    def test_r5_type_on_r4_warns(self) -> None:
        q = Questionnaire(
            url="http://example.org/q1",
            item=[
                QuestionnaireItem(
                    link_id="1", text="Code", type=QuestionnaireItemType.CODING
                ),
            ],
        )
        q = set_fhir_version(q, FhirVersion.R4)
        warnings = validate(q)
        assert any("coding" in w and "R4" in w for w in warnings)

    def test_r5_type_on_r5_ok(self) -> None:
        q = Questionnaire(
            url="http://example.org/q1",
            item=[
                QuestionnaireItem(
                    link_id="1", text="Code", type=QuestionnaireItemType.CODING
                ),
            ],
        )
        q = set_fhir_version(q, FhirVersion.R5)
        warnings = validate(q)
        assert not any("coding" in w for w in warnings)


def _make_q_with_choice_item() -> Questionnaire:
    """Helper: questionnaire with a choice item that has valueCoding options."""
    q = Questionnaire(url="http://example.org/q1", title="Test")
    item = QuestionnaireItem(
        link_id="1",
        text="Gender",
        type=QuestionnaireItemType.CHOICE,
        answer_option=[
            {
                "valueCoding": {
                    "system": "http://hl7.org/fhir/administrative-gender",
                    "code": "male",
                    "display": "Male",
                }
            },
            {
                "valueCoding": {
                    "system": "http://hl7.org/fhir/administrative-gender",
                    "code": "female",
                    "display": "Female",
                }
            },
        ],
    )
    return add_item(q, item)


def _make_q_with_string_options() -> Questionnaire:
    """Helper: questionnaire with valueString answer options."""
    q = Questionnaire(url="http://example.org/q1", title="Test")
    item = QuestionnaireItem(
        link_id="1",
        text="Pick one",
        type=QuestionnaireItemType.CHOICE,
        answer_option=[
            {"valueString": "Option A"},
            {"valueString": "Option B"},
        ],
    )
    return add_item(q, item)


def _get_extra(model: object, key: str) -> object | None:
    extras = getattr(model, "__pydantic_extra__", None)
    if extras is None:
        return None
    return extras.get(key)


class TestAddTranslation:
    def test_translate_item_text(self, questionnaire_with_items: Questionnaire) -> None:
        result = add_translation(questionnaire_with_items, "nl", "Naam", link_id="1")
        item = find_item(result.item, "1")
        underscore_text = _get_extra(item, "_text")
        assert underscore_text is not None
        exts = underscore_text["extension"]
        assert len(exts) == 1
        assert exts[0]["url"] == TRANSLATION_URL
        sub_exts = exts[0]["extension"]
        assert {"url": "lang", "valueCode": "nl"} in sub_exts
        assert {"url": "content", "valueString": "Naam"} in sub_exts

    def test_translate_nested_item(
        self, questionnaire_with_items: Questionnaire
    ) -> None:
        result = add_translation(questionnaire_with_items, "fr", "Âge", link_id="2.1")
        item = find_item(result.item, "2.1")
        underscore_text = _get_extra(item, "_text")
        assert underscore_text is not None

    def test_two_languages(self, questionnaire_with_items: Questionnaire) -> None:
        result = add_translation(questionnaire_with_items, "nl", "Naam", link_id="1")
        result = add_translation(result, "fr", "Nom", link_id="1")
        item = find_item(result.item, "1")
        exts = _get_extra(item, "_text")["extension"]
        assert len(exts) == 2

    def test_upsert_same_language(
        self, questionnaire_with_items: Questionnaire
    ) -> None:
        result = add_translation(questionnaire_with_items, "nl", "Naam", link_id="1")
        result = add_translation(result, "nl", "Voornaam", link_id="1")
        item = find_item(result.item, "1")
        exts = _get_extra(item, "_text")["extension"]
        assert len(exts) == 1
        assert exts[0]["extension"][1]["valueString"] == "Voornaam"

    def test_translate_title(self, empty_questionnaire: Questionnaire) -> None:
        result = add_translation(empty_questionnaire, "nl", "Inname", field="title")
        underscore_title = _get_extra(result, "_title")
        assert underscore_title is not None
        assert len(underscore_title["extension"]) == 1

    def test_translate_description(self, empty_questionnaire: Questionnaire) -> None:
        result = add_translation(
            empty_questionnaire, "de", "Beschreibung", field="description"
        )
        underscore_desc = _get_extra(result, "_description")
        assert underscore_desc is not None

    def test_item_not_found(self, empty_questionnaire: Questionnaire) -> None:
        with pytest.raises(ValueError, match="not found"):
            add_translation(empty_questionnaire, "nl", "test", link_id="999")

    def test_preserves_existing_extensions_on_text(
        self, questionnaire_with_items: Questionnaire
    ) -> None:
        """Non-translation extensions on _text should be preserved."""
        item = find_item(questionnaire_with_items.item, "1")
        existing_ext = {
            "url": "http://example.org/other",
            "valueString": "keep me",
        }
        item = item.model_copy(update={"_text": {"extension": [existing_ext]}})
        q = questionnaire_with_items.model_copy(
            update={
                "item": [item]
                + [i for i in questionnaire_with_items.item if i.link_id != "1"]
            }
        )
        result = add_translation(q, "nl", "Naam", link_id="1")
        updated_item = find_item(result.item, "1")
        exts = _get_extra(updated_item, "_text")["extension"]
        assert len(exts) == 2
        urls = [e["url"] for e in exts]
        assert "http://example.org/other" in urls
        assert TRANSLATION_URL in urls

    def test_translate_answer_by_code(self) -> None:
        q = _make_q_with_choice_item()
        result = add_translation(q, "nl", "Man", link_id="1", answer_code="male")
        item = find_item(result.item, "1")
        coding = item.answer_option[0]["valueCoding"]
        assert "_display" in coding
        exts = coding["_display"]["extension"]
        assert len(exts) == 1
        assert exts[0]["url"] == TRANSLATION_URL

    def test_translate_answer_by_index_coding(self) -> None:
        q = _make_q_with_choice_item()
        result = add_translation(q, "fr", "Femme", link_id="1", answer_index=1)
        item = find_item(result.item, "1")
        coding = item.answer_option[1]["valueCoding"]
        assert "_display" in coding

    def test_translate_answer_by_index_string(self) -> None:
        q = _make_q_with_string_options()
        result = add_translation(q, "nl", "Optie A", link_id="1", answer_index=0)
        item = find_item(result.item, "1")
        opt = item.answer_option[0]
        assert "_valueString" in opt
        exts = opt["_valueString"]["extension"]
        assert len(exts) == 1

    def test_answer_code_not_found(self) -> None:
        q = _make_q_with_choice_item()
        with pytest.raises(ValueError, match="No answerOption with code"):
            add_translation(q, "nl", "test", link_id="1", answer_code="nonexistent")
