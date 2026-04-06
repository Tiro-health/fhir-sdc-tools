"""Pure transform functions for Questionnaire manipulation.

All functions take a Questionnaire and return a new Questionnaire.
No mutation, no IO.
"""

from __future__ import annotations

import copy

from sdc.models import (
    ITEM_TYPES_FOR_VERSION,
    TRANSLATION_URL,
    EnableWhen,
    Extension,
    Questionnaire,
    QuestionnaireItem,
    resolve_fhir_version,
)


def find_item(items: list[QuestionnaireItem], link_id: str) -> QuestionnaireItem | None:
    """Recursively find an item by linkId."""
    for item in items:
        if item.link_id == link_id:
            return item
        if item.item:
            found = find_item(item.item, link_id)
            if found is not None:
                return found
    return None


def _map_items(
    items: list[QuestionnaireItem],
    link_id: str,
    fn: callable,
) -> list[QuestionnaireItem]:
    """Apply fn to the item matching link_id, recursively. Returns new list."""
    result: list[QuestionnaireItem] = []
    for item in items:
        if item.link_id == link_id:
            result.append(fn(item))
        elif item.item:
            result.append(
                item.model_copy(update={"item": _map_items(item.item, link_id, fn)})
            )
        else:
            result.append(item)
    return result


def _filter_items(
    items: list[QuestionnaireItem], link_id: str
) -> list[QuestionnaireItem]:
    """Remove item with link_id from tree. Returns new list."""
    result: list[QuestionnaireItem] = []
    for item in items:
        if item.link_id == link_id:
            continue
        if item.item:
            result.append(
                item.model_copy(update={"item": _filter_items(item.item, link_id)})
            )
        else:
            result.append(item)
    return result


def add_item(
    q: Questionnaire,
    new_item: QuestionnaireItem,
    parent_link_id: str | None = None,
) -> Questionnaire:
    """Add an item to the questionnaire. If parent_link_id is given, nest under it."""
    items = list(q.item or [])

    if parent_link_id is None:
        items.append(new_item)
        return q.model_copy(update={"item": items})

    if not q.item or find_item(q.item, parent_link_id) is None:
        raise ValueError(f"Parent item '{parent_link_id}' not found.")

    def _append_child(parent: QuestionnaireItem) -> QuestionnaireItem:
        children = list(parent.item or [])
        children.append(new_item)
        return parent.model_copy(update={"item": children})

    return q.model_copy(
        update={"item": _map_items(q.item, parent_link_id, _append_child)}
    )


def remove_item(q: Questionnaire, link_id: str) -> Questionnaire:
    """Remove an item by linkId from anywhere in the tree."""
    if not q.item:
        raise ValueError(f"Item '{link_id}' not found.")
    filtered = _filter_items(q.item, link_id)
    return q.model_copy(update={"item": filtered or None})


def add_enable_when(
    q: Questionnaire, link_id: str, enable_when: EnableWhen
) -> Questionnaire:
    """Add an enableWhen condition to an item."""
    if not q.item or find_item(q.item, link_id) is None:
        raise ValueError(f"Item '{link_id}' not found.")

    def _add_ew(item: QuestionnaireItem) -> QuestionnaireItem:
        ew_list = list(item.enable_when or [])
        ew_list.append(enable_when)
        return item.model_copy(update={"enable_when": ew_list})

    return q.model_copy(update={"item": _map_items(q.item, link_id, _add_ew)})


def set_enable_behavior(q: Questionnaire, link_id: str, behavior: str) -> Questionnaire:
    """Set enableBehavior (all/any) on an item."""
    if not q.item or find_item(q.item, link_id) is None:
        raise ValueError(f"Item '{link_id}' not found.")

    def _set_eb(item: QuestionnaireItem) -> QuestionnaireItem:
        return item.model_copy(update={"enable_behavior": behavior})

    return q.model_copy(update={"item": _map_items(q.item, link_id, _set_eb)})


def add_answer_option(
    q: Questionnaire, link_id: str, option: dict[str, object]
) -> Questionnaire:
    """Add an answerOption to a choice/open-choice item."""
    if not q.item or find_item(q.item, link_id) is None:
        raise ValueError(f"Item '{link_id}' not found.")

    def _add_opt(item: QuestionnaireItem) -> QuestionnaireItem:
        opts = list(item.answer_option or [])
        opts.append(option)
        return item.model_copy(update={"answer_option": opts})

    return q.model_copy(update={"item": _map_items(q.item, link_id, _add_opt)})


def set_answer_value_set(
    q: Questionnaire, link_id: str, value_set_url: str
) -> Questionnaire:
    """Set answerValueSet on an item."""
    if not q.item or find_item(q.item, link_id) is None:
        raise ValueError(f"Item '{link_id}' not found.")

    def _set_vs(item: QuestionnaireItem) -> QuestionnaireItem:
        return item.model_copy(update={"answer_value_set": value_set_url})

    return q.model_copy(update={"item": _map_items(q.item, link_id, _set_vs)})


def add_extension(
    q: Questionnaire,
    extension: Extension,
    link_id: str | None = None,
) -> Questionnaire:
    """Add an extension. If link_id is None, add to questionnaire level."""
    if link_id is None:
        exts = list(q.extension or [])
        exts.append(extension)
        return q.model_copy(update={"extension": exts})

    if not q.item or find_item(q.item, link_id) is None:
        raise ValueError(f"Item '{link_id}' not found.")

    def _add_ext(item: QuestionnaireItem) -> QuestionnaireItem:
        exts = list(item.extension or [])
        exts.append(extension)
        return item.model_copy(update={"extension": exts})

    return q.model_copy(update={"item": _map_items(q.item, link_id, _add_ext)})


def remove_extension(
    q: Questionnaire,
    extension_url: str,
    link_id: str | None = None,
) -> Questionnaire:
    """Remove extensions by URL. If link_id is None, remove from questionnaire level."""
    if link_id is None:
        exts = [e for e in (q.extension or []) if e.url != extension_url]
        return q.model_copy(update={"extension": exts or None})

    if not q.item or find_item(q.item, link_id) is None:
        raise ValueError(f"Item '{link_id}' not found.")

    def _rm_ext(item: QuestionnaireItem) -> QuestionnaireItem:
        exts = [e for e in (item.extension or []) if e.url != extension_url]
        return item.model_copy(update={"extension": exts or None})

    return q.model_copy(update={"item": _map_items(q.item, link_id, _rm_ext)})


def set_meta(q: Questionnaire, **fields: object) -> Questionnaire:
    """Set top-level metadata fields."""
    return q.model_copy(update=fields)


def validate(q: Questionnaire) -> list[str]:
    """Validate questionnaire structure. Returns list of warning messages."""
    warnings: list[str] = []
    version = resolve_fhir_version(q)

    if not q.url:
        warnings.append("Questionnaire has no url.")
    if not q.item:
        warnings.append("Questionnaire has no items.")
        return warnings

    # Check unique linkIds
    link_ids: list[str] = []
    _collect_link_ids(q.item, link_ids)
    seen: set[str] = set()
    for lid in link_ids:
        if lid in seen:
            warnings.append(f"Duplicate linkId: '{lid}'.")
        seen.add(lid)

    # Check enableWhen references
    all_ids = set(link_ids)
    _check_enable_when_refs(q.item, all_ids, warnings)

    # Check item types against FHIR version
    valid_types = ITEM_TYPES_FOR_VERSION[version]
    _check_item_types(q.item, valid_types, version, warnings)

    return warnings


def _collect_link_ids(items: list[QuestionnaireItem], result: list[str]) -> None:
    for item in items:
        result.append(item.link_id)
        if item.item:
            _collect_link_ids(item.item, result)


def _check_enable_when_refs(
    items: list[QuestionnaireItem],
    all_ids: set[str],
    warnings: list[str],
) -> None:
    for item in items:
        for ew in item.enable_when or []:
            if ew.question not in all_ids:
                warnings.append(
                    f"enableWhen on '{item.link_id}' references "
                    f"unknown linkId '{ew.question}'."
                )
        if item.item:
            _check_enable_when_refs(item.item, all_ids, warnings)


def _check_item_types(
    items: list[QuestionnaireItem],
    valid_types: set[str],
    version: object,
    warnings: list[str],
) -> None:
    for item in items:
        if item.type.value not in valid_types:
            warnings.append(
                f"Item '{item.link_id}' has type '{item.type}' "
                f"which is not valid in FHIR {version}."
            )
        if item.item:
            _check_item_types(item.item, valid_types, version, warnings)


# --- Translation ---


def _build_translation_extension(lang: str, value: str) -> dict[str, object]:
    """Build a single FHIR translation extension dict."""
    return {
        "url": TRANSLATION_URL,
        "extension": [
            {"url": "lang", "valueCode": lang},
            {"url": "content", "valueString": value},
        ],
    }


def _is_translation_for_lang(ext: dict[str, object], lang: str) -> bool:
    """Check if an extension is a translation for the given language."""
    if ext.get("url") != TRANSLATION_URL:
        return False
    for sub in ext.get("extension", []):
        if sub.get("url") == "lang" and sub.get("valueCode") == lang:
            return True
    return False


def _upsert_translation(
    existing: dict[str, object] | None, lang: str, value: str
) -> dict[str, object]:
    """Add or replace a translation in a _ companion property dict."""
    exts = list((existing or {}).get("extension", []))
    exts = [e for e in exts if not _is_translation_for_lang(e, lang)]
    exts.append(_build_translation_extension(lang, value))
    return {"extension": exts}


def _get_extra(model: object, key: str) -> object | None:
    """Get an extra field from a Pydantic model with extra='allow'."""
    extras = getattr(model, "__pydantic_extra__", None)
    if extras is None:
        return None
    return extras.get(key)


def _translate_answer_option_by_code(
    item: QuestionnaireItem, answer_code: str, lang: str, value: str
) -> QuestionnaireItem:
    """Translate the display of an answerOption matched by valueCoding.code."""
    if not item.answer_option:
        raise ValueError(f"Item '{item.link_id}' has no answerOptions.")
    new_options = list(item.answer_option)
    for i, opt in enumerate(new_options):
        coding = opt.get("valueCoding")
        if coding and coding.get("code") == answer_code:
            coding = copy.deepcopy(coding)
            coding["_display"] = _upsert_translation(
                coding.get("_display"), lang, value
            )
            new_options[i] = {**opt, "valueCoding": coding}
            return item.model_copy(update={"answer_option": new_options})
    raise ValueError(
        f"No answerOption with code '{answer_code}' on item '{item.link_id}'."
    )


def _translate_answer_option_by_index(
    item: QuestionnaireItem, answer_index: int, lang: str, value: str
) -> QuestionnaireItem:
    """Translate an answerOption at the given index."""
    if not item.answer_option or answer_index >= len(item.answer_option):
        raise ValueError(
            f"answerOption index {answer_index} out of range on item '{item.link_id}'."
        )
    new_options = list(item.answer_option)
    opt = copy.deepcopy(new_options[answer_index])
    if "valueCoding" in opt:
        coding = opt["valueCoding"]
        coding["_display"] = _upsert_translation(coding.get("_display"), lang, value)
    elif "valueString" in opt:
        opt["_valueString"] = _upsert_translation(opt.get("_valueString"), lang, value)
    else:
        raise ValueError(
            f"answerOption at index {answer_index} on item '{item.link_id}' "
            f"has no valueCoding or valueString."
        )
    new_options[answer_index] = opt
    return item.model_copy(update={"answer_option": new_options})


def add_translation(
    q: Questionnaire,
    lang: str,
    value: str,
    link_id: str | None = None,
    field: str | None = None,
    answer_code: str | None = None,
    answer_index: int | None = None,
) -> Questionnaire:
    """Add a translation extension.

    Modes:
    - field set: translate questionnaire-level field (title/description)
    - link_id only: translate item text
    - link_id + answer_code: translate answer option display by code
    - link_id + answer_index: translate answer option by index
    """
    if field is not None:
        underscore_key = f"_{field}"
        existing = _get_extra(q, underscore_key)
        updated = _upsert_translation(existing, lang, value)
        return q.model_copy(update={underscore_key: updated})

    if link_id is None:
        raise ValueError("Provide link_id or field.")

    if not q.item or find_item(q.item, link_id) is None:
        raise ValueError(f"Item '{link_id}' not found.")

    if answer_code is not None:

        def _translate_by_code(item: QuestionnaireItem) -> QuestionnaireItem:
            return _translate_answer_option_by_code(item, answer_code, lang, value)

        return q.model_copy(
            update={"item": _map_items(q.item, link_id, _translate_by_code)}
        )

    if answer_index is not None:

        def _translate_by_index(item: QuestionnaireItem) -> QuestionnaireItem:
            return _translate_answer_option_by_index(item, answer_index, lang, value)

        return q.model_copy(
            update={"item": _map_items(q.item, link_id, _translate_by_index)}
        )

    # Default: translate item text
    def _translate_text(item: QuestionnaireItem) -> QuestionnaireItem:
        existing = _get_extra(item, "_text")
        updated = _upsert_translation(existing, lang, value)
        return item.model_copy(update={"_text": updated})

    return q.model_copy(update={"item": _map_items(q.item, link_id, _translate_text)})


# --- Text extraction ---


def extract_texts(q: Questionnaire) -> list[dict[str, str]]:
    """Extract all translatable strings from a questionnaire.

    Returns list of dicts with keys: linkId, field, answer_code, answer_index, text.
    """
    rows: list[dict[str, str]] = []

    # Questionnaire-level fields
    if q.name:
        rows.append(
            {
                "linkId": "",
                "field": "name",
                "answer_code": "",
                "answer_index": "",
                "text": q.name,
            }
        )
    if q.title:
        rows.append(
            {
                "linkId": "",
                "field": "title",
                "answer_code": "",
                "answer_index": "",
                "text": q.title,
            }
        )
    if q.description:
        rows.append(
            {
                "linkId": "",
                "field": "description",
                "answer_code": "",
                "answer_index": "",
                "text": q.description,
            }
        )

    # Items
    if q.item:
        _extract_items(q.item, rows)

    return rows


def _extract_items(items: list[QuestionnaireItem], rows: list[dict[str, str]]) -> None:
    for item in items:
        if item.text:
            rows.append(
                {
                    "linkId": item.link_id,
                    "field": "text",
                    "answer_code": "",
                    "answer_index": "",
                    "text": item.text,
                }
            )
        for i, opt in enumerate(item.answer_option or []):
            coding = opt.get("valueCoding")
            if coding and coding.get("display"):
                rows.append(
                    {
                        "linkId": item.link_id,
                        "field": "answer",
                        "answer_code": coding.get("code", ""),
                        "answer_index": str(i),
                        "text": coding["display"],
                    }
                )
            elif opt.get("valueString"):
                rows.append(
                    {
                        "linkId": item.link_id,
                        "field": "answer",
                        "answer_code": "",
                        "answer_index": str(i),
                        "text": opt["valueString"],
                    }
                )
        if item.item:
            _extract_items(item.item, rows)
