---
name: sdc-builder
description: "Build and preview FHIR SDC Questionnaires using the fhir-sdc-tools CLI or Python library. Use when: (1) Creating or modifying FHIR Questionnaires programmatically, (2) Adding items, extensions, enableWhen logic, answer options, or translations to questionnaires, (3) Validating questionnaire structure, (4) Previewing questionnaires with the Tiro renderer. Triggers: 'build questionnaire', 'create questionnaire', 'SDC form', 'add item to questionnaire', 'questionnaire builder', 'preview questionnaire', 'render questionnaire'."
---

# SDC Questionnaire Builder

Build FHIR SDC Questionnaires using the `fhir-sdc-tools` CLI or Python library, and preview them with the `render-questionnaire` MCP tool.

## Setup

Before first use, ensure the library is installed:

```bash
uv pip install fhir-sdc-tools
```

If `uv` is not available, fall back to `pip install fhir-sdc-tools --break-system-packages`.

If the environment has Python < 3.10 and `uv` is available, create a venv with a supported version first:

```bash
uv venv --python 3.11 .venv-sdc && source .venv-sdc/bin/activate
uv pip install fhir-sdc-tools
```

The `render-questionnaire` MCP tool is provided by this plugin automatically.

## How to Build Questionnaires

There are two approaches: the **CLI pipe workflow** (preferred for most cases) and the **Python API**. The CLI is more concise and composes well; use the Python API when you need programmatic control (loops, conditionals, reading existing files).

### CLI pipe workflow (preferred)

The `sdc` CLI reads JSON from stdin and writes to stdout. Chain commands with pipes to build questionnaires incrementally:

```bash
sdc init --url http://example.org/intake --title "Intake form" \
  | sdc item add --link-id name --text "Full name" --type string --required \
  | sdc item add --link-id dob --text "Date of birth" --type date --required \
  | sdc item add --link-id gender --text "Gender" --type choice \
  | sdc answer-option add --link-id gender --value-coding "http://hl7.org/fhir/administrative-gender|male|Male" \
  | sdc answer-option add --link-id gender --value-coding "http://hl7.org/fhir/administrative-gender|female|Female" \
  | sdc extension add --link-id gender --name itemControl --value-code drop-down \
  | sdc validate
```

Key CLI commands:

- `sdc init --url URL --title TITLE` — create a new questionnaire
- `sdc item add --link-id ID --text TEXT --type TYPE [--parent PARENT_ID] [--required] [--repeats]` — add an item
- `sdc item remove --link-id ID` — remove an item
- `sdc answer-option add --link-id ID --value-coding "system|code|display"` — add a coded answer option
- `sdc answer-option add --link-id ID --value-string "text"` — add a string answer option
- `sdc extension add --name SHORTHAND --expression "..." --description "..."` — add an SDC extension using a shorthand name
- `sdc extension add --link-id ID --name hidden --value-boolean true` — hide an item
- `sdc enable-when add --link-id ID --question SOURCE_ID --operator OP --answer-boolean true` — conditional display
- `sdc meta --status active --publisher "Org"` — set metadata
- `sdc translate --link-id ID --lang nl --value "Dutch text"` — add translations
- `sdc validate` — validate and pass through (warnings to stderr)

#### CLI example with variables and calculated expressions

```bash
sdc init --url http://example.org/bmi --title "BMI calculator" \
  | sdc item add --link-id grp --text "BMI calculator" --type group \
  | sdc extension add --link-id grp --name variable \
      --expression "QuestionnaireResponse.item.where(linkId='weight').answer.value" \
      --description weight \
  | sdc extension add --link-id grp --name variable \
      --expression "QuestionnaireResponse.item.where(linkId='height').answer.value" \
      --description height \
  | sdc extension add --link-id grp --name variable \
      --expression "iif(%weight.exists() and %height > 0, (%weight / (%height / 100).power(2)).round(1), {})" \
      --description bmi \
  | sdc item add --link-id weight --text "Weight (kg)" --type decimal --required --parent grp \
  | sdc item add --link-id height --text "Height (cm)" --type decimal --required --parent grp \
  | sdc item add --link-id bmi-result --text "Your BMI" --type decimal --parent grp \
  | sdc extension add --link-id bmi-result --name calculatedExpression \
      --expression "%bmi" \
  | sdc validate
```

### Python API

Use the Python API when you need programmatic control. The library uses **immutable transforms** — each function returns a new `Questionnaire`, so chain calls by reassigning.

```python
from sdc import (
    Questionnaire, QuestionnaireItem, QuestionnaireItemType,
    FhirVersion, add_item, set_fhir_version, validate,
)

q = Questionnaire(url="http://example.org/intake", title="Intake Form")
q = set_fhir_version(q, FhirVersion.R4)
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
2. **Build** — use the CLI pipe workflow (preferred) or write a Python script
3. **Validate** — pipe through `sdc validate` or call `validate(q)` in Python
4. **Save** — write JSON to a file (CLI: `| tee output.json`, Python: `pathlib.Path(...).write_text(...)`)
5. **Preview** — use the `render-questionnaire` MCP tool to preview the form visually

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

- **R5** (default for the Tiro renderer): Replaces `choice`/`open-choice` with `coding` type; adds `question` type
- **R4**: Uses `choice` and `open-choice` item types for coded answers
- The `sdc` CLI and Python library default to R4 if no version is set. To match the renderer, explicitly set R5: `--fhir-version R5` on `sdc init`, or `set_fhir_version(q, FhirVersion.R5)` in Python, or set `SDC_FHIR_VERSION=R5` as an environment variable

## Tips

- Always call `validate(q)` before outputting — it checks unique linkIds, enableWhen references, and item type validity
- Use `by_alias=True` in `model_dump_json()` — this serializes Python `snake_case` fields as FHIR `camelCase` (e.g., `link_id` → `linkId`)
- Use `exclude_none=True` to produce clean FHIR JSON
- For nested items, pass `parent_link_id` to `add_item()`
- SDC extension shortcuts: `hidden`, `itemControl`, `variable`, `calculatedExpression`, `initialExpression`, `enableWhenExpression`, `candidateExpression`, `answerExpression`
