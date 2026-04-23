---
name: sdc-builder
description: "Build and preview FHIR SDC Questionnaires using the fhir-sdc-tools library (Python API or `sdc` CLI). Use when: (1) Creating or modifying FHIR Questionnaires programmatically, (2) Adding items, extensions, enableWhen logic, answer options, or translations to questionnaires, (3) Validating questionnaire structure, (4) Previewing questionnaires with the Tiro renderer. Triggers: 'build questionnaire', 'create questionnaire', 'SDC form', 'add item to questionnaire', 'questionnaire builder', 'preview questionnaire', 'render questionnaire'."
---

# SDC Questionnaire Builder

Build FHIR SDC Questionnaires using the `fhir-sdc-tools` package — either the Python API or the composable `sdc` CLI — and preview them with the `render-questionnaire` MCP tool.

## Setup

Before first use, ensure the package is installed:

```bash
uv pip install fhir-sdc-tools
```

If `uv` is not available, fall back to `pip install fhir-sdc-tools`. Installation exposes both the `sdc` import (Python) and the `sdc` command (CLI).

The `render-questionnaire` MCP tool is provided by this plugin automatically.

## Choosing Python vs CLI

Both interfaces produce the same FHIR JSON. Pick based on the task shape:

- **Python API** — programmatic generation, loops, reading external data, conditional logic across many items, or anything with dynamic answer lists. Best when the construction logic itself needs code.
- **CLI** — quick one-off forms, shell-driven pipelines, demos, and interactive exploration. Readable as a single chain of commands and friendly to copy-paste. Used heavily by the `calculator-builder` skill.

You can mix: build scaffolding with the CLI, then load the JSON in Python to add complex items.

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

## CLI usage

The `sdc` CLI is composable: every command (except `init`) reads a Questionnaire JSON from stdin and writes to stdout, so forms are built by piping commands together.

### Minimal example

```bash
sdc init --url http://example.org/intake --title "Intake Form" \
  | sdc item add --link-id name --text "Full name" --type string --required \
  | sdc item add --link-id dob  --text "Date of birth" --type date \
  | sdc validate \
  > questionnaire.json
```

`sdc validate` writes warnings to **stderr** and passes the JSON through on stdout, so it's safe to leave in the middle of a pipe. Redirect stderr separately (`2>/tmp/warnings.txt`) if warnings are corrupting downstream consumers.

### Command map

| Command | Purpose |
|---|---|
| `sdc init` | Create an empty Questionnaire (`--url`, `--title`, `--name`, `--status`, `--fhir-version`). Only command that does *not* read stdin. |
| `sdc meta` | Update top-level fields (`--status`, `--publisher`, `--description`, `--name`, `--title`, `--url`, `--language`). |
| `sdc item add` | Add an item (`--link-id`, `--type`, `--text`, `--parent`, `--required`, `--repeats`, `--definition`). |
| `sdc item remove` | Remove an item by linkId (searches the full tree). |
| `sdc answer-option add` | Add an answer option to a choice/coding item. One of `--value-string`, `--value-integer`, `--value-coding`; optional `--weight` attaches an `itemWeight` extension. |
| `sdc answer-option set-value-set` | Bind `answerValueSet` instead of inline options. |
| `sdc answer-option set-weight` | Set `itemWeight` on an existing answer option. |
| `sdc enable-when add` | Add conditional visibility (`--question`, `--operator`, one `--answer-*`). |
| `sdc enable-when set-behavior` | Set `enableBehavior` to `all` or `any`. |
| `sdc extension add <shorthand>` | SDC shortcuts: `hidden`, `item-control`, `variable`, `calculated-expression`, `initial-expression`, `enable-when-expression`, `candidate-expression`, `answer-expression`. |
| `sdc extension add custom` | Arbitrary extension by URL. |
| `sdc extension remove` | Remove extensions by URL. |
| `sdc translate` | Add a translation for item text, answer option, or questionnaire-level `title`/`description`. |
| `sdc extract-texts` | Dump translatable strings to CSV (optionally with `--langs fr,en` columns). |
| `sdc apply-translations` | Apply a filled-in CSV back onto the Questionnaire. |
| `sdc composition` / `sdc template` | Build Composition templates for SDC template-based extraction. |
| `sdc validate` | Structural validation (unique linkIds, enableWhen refs, item types vs FHIR version). Warnings to stderr, JSON to stdout. |

Run `sdc <command> --help` for full flag lists and examples.

### Variables and calculated expressions

`sdc extension add variable` omits `--link-id` to attach at the questionnaire level (accessible to all siblings). Pair with `sdc extension add calculated-expression --link-id <target>` to consume the variable in a result field. See the `calculator-builder` skill for FHIRPath patterns and scoping caveats.

### Long pipelines

Very long CLI chains can hit argument length or stdin buffering limits. For complex forms, stage the build into intermediate files:

```bash
sdc init ... | sdc item add ... | sdc item add ... > /tmp/stage1.json
sdc extension add variable ... < /tmp/stage1.json | sdc validate > final.json
```

### FHIR version

Set with `--fhir-version r4|r5` on `sdc init`, or export `SDC_FHIR_VERSION=R5`. R5 is the default.

## API Reference

See [references/api.md](references/api.md) for the complete Python function and model reference.

## Workflow

### Building a new questionnaire

1. **Install** — run `uv pip install fhir-sdc-tools` if not already present
2. **Build** — either write a Python script using the API, or compose a pipeline of `sdc` CLI commands
3. **Run** — `python script.py` or execute the pipeline, producing FHIR JSON
4. **Validate** — call `validate(q)` / end the CLI chain with `sdc validate`; fix any warnings
5. **Save** — write the JSON to a file
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
