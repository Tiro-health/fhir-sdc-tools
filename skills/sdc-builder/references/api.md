# fhir-sdc-tools API Reference

All imports from `sdc`:

```python
from sdc import (
    # Models
    Questionnaire, QuestionnaireItem, QuestionnaireItemType,
    EnableWhen, EnableWhenOperator, Extension,
    FhirVersion, PublicationStatus, Meta, SDC_URLS,
    # Functions
    add_item, remove_item, find_item,
    add_enable_when, set_enable_behavior,
    add_answer_option, set_answer_value_set,
    add_extension, remove_extension,
    set_meta, validate,
    add_translation, extract_texts,
    set_fhir_version, resolve_fhir_version,
)
```

## Models

### Questionnaire

Top-level FHIR Questionnaire resource.

```python
q = Questionnaire(
    url="http://example.org/q1",      # Canonical URL
    title="My Form",                   # Human-readable title
    status=PublicationStatus.DRAFT,     # draft | active | retired | unknown
    name="my-form",                    # Computer-friendly name (optional)
    publisher="Org name",              # Publisher (optional)
    description="A form",             # Description (optional)
)
```

### QuestionnaireItem

A single item (question, group, or display).

```python
item = QuestionnaireItem(
    link_id="q1",                              # Unique ID (required) — serializes as "linkId"
    text="What is your name?",                 # Display text
    type=QuestionnaireItemType.STRING,          # Item type (required)
    required=True,                             # Is required? (optional)
    repeats=True,                              # Allow repeats? (optional)
    read_only=True,                            # Read-only? (optional)
    definition="http://...#Patient.name",      # Element definition URI (optional)
)
```

### QuestionnaireItemType (enum)

```
GROUP, DISPLAY, BOOLEAN, DECIMAL, INTEGER, DATE, DATE_TIME, TIME,
STRING, TEXT, URL, CHOICE, OPEN_CHOICE, ATTACHMENT, REFERENCE, QUANTITY,
CODING (R5 only), QUESTION (R5 only)
```

### EnableWhen

Conditional display rule.

```python
ew = EnableWhen.model_validate({
    "question": "q1",           # Source question linkId
    "operator": "=",            # exists | = | != | > | < | >= | <=
    "answerBoolean": True,      # Answer value (type matches source question)
})
```

Answer value keys: `answerBoolean`, `answerString`, `answerInteger`, `answerCoding`, etc.

### Extension

FHIR Extension.

```python
ext = Extension.model_validate({
    "url": "http://hl7.org/fhir/StructureDefinition/questionnaire-hidden",
    "valueBoolean": True,
})
```

### SDC_URLS (dict)

Shorthand names to full SDC extension URLs:

```python
SDC_URLS = {
    "hidden":                "http://hl7.org/fhir/StructureDefinition/questionnaire-hidden",
    "itemControl":           "http://hl7.org/fhir/StructureDefinition/questionnaire-itemControl",
    "variable":              "http://hl7.org/fhir/StructureDefinition/variable",
    "calculatedExpression":  "http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire-calculatedExpression",
    "initialExpression":     "http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire-initialExpression",
    "enableWhenExpression":  "http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire-enableWhenExpression",
    "candidateExpression":   "http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire-candidateExpression",
    "answerExpression":      "http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire-answerExpression",
}
```

## Transform Functions

All functions are **pure** — they return a new Questionnaire without mutating the input.

### add_item(q, new_item, parent_link_id=None) → Questionnaire

Add an item. If `parent_link_id` is given, nests under that parent.

```python
q = add_item(q, QuestionnaireItem(link_id="1", text="Name", type=QuestionnaireItemType.STRING))
q = add_item(q, QuestionnaireItem(link_id="1.1", text="First", type=QuestionnaireItemType.STRING), parent_link_id="1")
```

### remove_item(q, link_id) → Questionnaire

Remove an item by linkId from anywhere in the tree.

### find_item(items, link_id) → QuestionnaireItem | None

Find an item by linkId in a list of items (recursive).

### add_enable_when(q, link_id, enable_when) → Questionnaire

Add an enableWhen condition to an item.

```python
ew = EnableWhen.model_validate({"question": "q1", "operator": "=", "answerBoolean": True})
q = add_enable_when(q, "q2", ew)
```

### set_enable_behavior(q, link_id, behavior) → Questionnaire

Set enableBehavior ("all" or "any") on an item with multiple enableWhen conditions.

### add_answer_option(q, link_id, option) → Questionnaire

Add an answer option to a choice/coding item.

```python
# String option
q = add_answer_option(q, "q1", {"valueString": "Option A"})

# Coded option
q = add_answer_option(q, "q1", {
    "valueCoding": {"system": "http://snomed.info/sct", "code": "73211009", "display": "Diabetes"}
})

# Integer option
q = add_answer_option(q, "q1", {"valueInteger": 42})
```

### set_answer_value_set(q, link_id, value_set_url) → Questionnaire

Set answerValueSet on an item (alternative to inline answer options).

```python
q = set_answer_value_set(q, "gender", "http://hl7.org/fhir/ValueSet/administrative-gender")
```

### add_extension(q, extension, link_id=None) → Questionnaire

Add an extension. If `link_id` is None, adds to the questionnaire level.

```python
# Hidden item
ext = Extension.model_validate({"url": SDC_URLS["hidden"], "valueBoolean": True})
q = add_extension(q, ext, link_id="secret-field")

# Calculated expression
ext = Extension.model_validate({
    "url": SDC_URLS["calculatedExpression"],
    "valueExpression": {
        "language": "text/fhirpath",
        "expression": "%weight / (%height / 100).power(2)",
    },
})
q = add_extension(q, ext, link_id="bmi")

# Variable (questionnaire-level)
ext = Extension.model_validate({
    "url": SDC_URLS["variable"],
    "valueExpression": {
        "language": "text/fhirpath",
        "description": "weight",
        "expression": "%resource.item.where(linkId='weight').answer.value",
    },
})
q = add_extension(q, ext)

# itemControl (drop-down)
ext = Extension.model_validate({
    "url": SDC_URLS["itemControl"],
    "valueCodeableConcept": {"coding": [{"code": "drop-down"}]},
})
q = add_extension(q, ext, link_id="q1")
```

### remove_extension(q, extension_url, link_id=None) → Questionnaire

Remove all extensions matching the URL.

### set_meta(q, **fields) → Questionnaire

Set top-level metadata fields.

```python
q = set_meta(q, status=PublicationStatus.ACTIVE, publisher="My Org", language="en")
```

### validate(q) → list[str]

Validate questionnaire structure. Returns list of warning strings (empty = valid).

Checks:
- Questionnaire has a URL
- Questionnaire has items
- All linkIds are unique
- enableWhen references point to existing linkIds
- Item types are valid for the detected FHIR version

### add_translation(q, lang, value, link_id=None, field=None, answer_code=None, answer_index=None) → Questionnaire

Add a FHIR translation extension.

```python
# Translate item text
q = add_translation(q, "nl", "Wat is uw naam?", link_id="name")

# Translate questionnaire title
q = add_translation(q, "nl", "Inname Formulier", field="title")

# Translate answer option by code
q = add_translation(q, "nl", "Man", link_id="gender", answer_code="male")

# Translate answer option by index
q = add_translation(q, "nl", "Optie A", link_id="q1", answer_index=0)
```

### extract_texts(q) → list[dict]

Extract all translatable strings. Returns list of dicts with keys: `linkId`, `field`, `answer_code`, `answer_index`, `text`.

### set_fhir_version(q, version) → Questionnaire

Set FHIR version in meta.profile.

### resolve_fhir_version(q=None) → FhirVersion

Resolve FHIR version: questionnaire profile > `SDC_FHIR_VERSION` env var > R5 default.

## Complete Example: Patient Intake Form

```python
from sdc import (
    Questionnaire, QuestionnaireItem, QuestionnaireItemType,
    EnableWhen, Extension, FhirVersion, SDC_URLS,
    add_item, add_enable_when, add_answer_option, add_extension,
    set_fhir_version, set_meta, validate,
)
import json, pathlib

# Create questionnaire
q = Questionnaire(url="http://example.org/intake", title="Patient Intake")
q = set_fhir_version(q, FhirVersion.R5)
q = set_meta(q, language="en", publisher="Example Hospital")

# Add items
q = add_item(q, QuestionnaireItem(link_id="name", text="Full name", type=QuestionnaireItemType.STRING, required=True))
q = add_item(q, QuestionnaireItem(link_id="dob", text="Date of birth", type=QuestionnaireItemType.DATE, required=True))
q = add_item(q, QuestionnaireItem(link_id="has-allergies", text="Do you have any allergies?", type=QuestionnaireItemType.BOOLEAN))

# Conditional group — only shown if has-allergies is true
q = add_item(q, QuestionnaireItem(link_id="allergy-details", text="Allergy details", type=QuestionnaireItemType.GROUP))
ew = EnableWhen.model_validate({"question": "has-allergies", "operator": "=", "answerBoolean": True})
q = add_enable_when(q, "allergy-details", ew)

# Nested item inside the group
q = add_item(q, QuestionnaireItem(link_id="allergy-name", text="Allergy name", type=QuestionnaireItemType.STRING, repeats=True), parent_link_id="allergy-details")

# Choice with answer options
q = add_item(q, QuestionnaireItem(link_id="severity", text="Severity", type=QuestionnaireItemType.CHOICE), parent_link_id="allergy-details")
q = add_answer_option(q, "severity", {"valueCoding": {"system": "http://example.org", "code": "mild", "display": "Mild"}})
q = add_answer_option(q, "severity", {"valueCoding": {"system": "http://example.org", "code": "moderate", "display": "Moderate"}})
q = add_answer_option(q, "severity", {"valueCoding": {"system": "http://example.org", "code": "severe", "display": "Severe"}})

# Make severity a drop-down
ext = Extension.model_validate({"url": SDC_URLS["itemControl"], "valueCodeableConcept": {"coding": [{"code": "drop-down"}]}})
q = add_extension(q, ext, link_id="severity")

# Validate
warnings = validate(q)
for w in warnings:
    print(f"WARNING: {w}")

# Write output
pathlib.Path("intake.json").write_text(q.model_dump_json(by_alias=True, exclude_none=True, indent=2))
print("Wrote intake.json")
```
