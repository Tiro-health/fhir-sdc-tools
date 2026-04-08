---
name: sdc-builder
description: "Build and preview FHIR SDC Questionnaires using the fhir-sdc-tools Python library. Use when: (1) Creating or modifying FHIR Questionnaires programmatically, (2) Adding items, extensions, enableWhen logic, answer options, or translations to questionnaires, (3) Validating questionnaire structure, (4) Previewing questionnaires with the Tiro renderer. Triggers: 'build questionnaire', 'create questionnaire', 'SDC form', 'add item to questionnaire', 'questionnaire builder', 'preview questionnaire', 'render questionnaire'."
---

# SDC Questionnaire Builder

Build FHIR SDC Questionnaires using the `fhir-sdc-tools` Python library and preview them with the `render-questionnaire` MCP tool.

## Setup

Before first use, ensure the library is installed:

```bash
uv pip install fhir-sdc-tools
```

If `uv` is not available, fall back to `pip install fhir-sdc-tools`.

The `render-questionnaire` MCP tool is provided by this plugin automatically.

## How to Build Questionnaires

Write a Python script that uses the `sdc` library to compose the questionnaire, then run it. The library uses **immutable transforms** — each function returns a new `Questionnaire`, so chain calls by reassigning.

### Minimal example

```python
from sdc import (
    Questionnaire, QuestionnaireItem, QuestionnaireItemType,
    FhirVersion, add_item, set_fhir_version, validate,
)

q = Questionnaire(url="http://example.org/intake", title="Intake Form")
q = set_fhir_version(q, FhirVersion.R5)
q = add_item(q, QuestionnaireItem(link_id="name", text="Full name", type=QuestionnaireItemType.STRING))
q = add_item(q, QuestionnaireItem(link_id="dob", text="Date of birth", type=QuestionnaireItemType.DATE))

warnings = validate(q)
if warnings:
    for w in warnings:
        print(f"WARNING: {w}")

print(q.model_dump_json(by_alias=True, exclude_none=True, indent=2))
```

### Output to file

Always write the final questionnaire JSON to a file so it can be rendered or shared:

```python
import json, pathlib
pathlib.Path("questionnaire.json").write_text(
    q.model_dump_json(by_alias=True, exclude_none=True, indent=2)
)
```

## API Reference

See [references/api.md](references/api.md) for the complete function and model reference.

## Workflow

### Building a new questionnaire

1. **Install** — run `uv pip install fhir-sdc-tools` if not already present
2. **Write a Python script** that creates the questionnaire using the API
3. **Run the script** via `python script.py` to produce the JSON
4. **Validate** — call `validate(q)` before outputting; fix any warnings
5. **Save** — write JSON to a file
6. **Preview** — use the `render-questionnaire` MCP tool to preview the form visually

### Modifying an existing questionnaire

```python
import json, pathlib
from sdc import Questionnaire, QuestionnaireItem, QuestionnaireItemType, add_item

data = json.loads(pathlib.Path("existing.json").read_text())
q = Questionnaire.model_validate(data)

# Make modifications
q = add_item(q, QuestionnaireItem(link_id="new-item", text="New question", type=QuestionnaireItemType.STRING))

pathlib.Path("existing.json").write_text(
    q.model_dump_json(by_alias=True, exclude_none=True, indent=2)
)
```

### Previewing

Use the `render-questionnaire` MCP tool to preview:
- Pass the questionnaire JSON object directly as the `questionnaire` parameter
- Or pass a canonical URL if the questionnaire is published on a FHIR server

## FHIR Version Notes

- **R4**: Uses `choice` and `open-choice` item types for coded answers
- **R5** (default): Replaces `choice`/`open-choice` with `coding` type; adds `question` type
- Set version explicitly with `set_fhir_version(q, FhirVersion.R5)` or detect from env var `SDC_FHIR_VERSION`

## Tips

- Always call `validate(q)` before outputting — it checks unique linkIds, enableWhen references, and item type validity
- Use `by_alias=True` in `model_dump_json()` — this serializes Python `snake_case` fields as FHIR `camelCase` (e.g., `link_id` → `linkId`)
- Use `exclude_none=True` to produce clean FHIR JSON
- For nested items, pass `parent_link_id` to `add_item()`
- SDC extension shortcuts: `hidden`, `itemControl`, `variable`, `calculatedExpression`, `initialExpression`, `enableWhenExpression`, `candidateExpression`, `answerExpression`
- Custom extensions: `add_extension()` accepts any URL, not just `SDC_URLS` shortcuts — use `Extension.model_validate({"url": "http://example.org/ext", "valueString": "..."})` for arbitrary extensions
