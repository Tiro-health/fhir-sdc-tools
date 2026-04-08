# fhir-sdc-tools

Composable Python library and CLI for building FHIR SDC Questionnaires, with an MCP server for interactive previews.

## Quick start: Claude Code plugin

Install everything (MCP server + skill + CLI) as a plugin. Inside Claude Code:

```
/plugin marketplace add Tiro-health/fhir-sdc-tools
/plugin install fhir-sdc-tools
```

This gives you:
- `render-questionnaire` MCP tool for interactive previews
- `sdc-builder` skill that teaches Claude to build questionnaires using the Python API
- `sdc` CLI for shell-based workflows

## Quick start: Claude Desktop / claude.ai

Add to your Claude Desktop config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "Tiro Questionnaire": {
      "command": "uvx",
      "args": ["--from", "fhir-sdc-tools[mcp]", "fhir-sdc-mcp"]
    }
  }
}
```

Restart Claude Desktop. The `render-questionnaire` tool will appear in the tools menu.

> **Prerequisite**: [uv](https://docs.astral.sh/uv/getting-started/installation/) must be installed.

## Quick start: Claude Code

```bash
claude mcp add "Tiro Questionnaire" -- uvx --from "fhir-sdc-tools[mcp]" fhir-sdc-mcp
```

## Python library

```bash
pip install fhir-sdc-tools
```

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
print(q.model_dump_json(by_alias=True, exclude_none=True, indent=2))
```

## CLI

```bash
pip install fhir-sdc-tools

sdc init --url http://example.org/q1 --title "My Form" \
  | sdc item add --link-id 1 --text "Name" --type string \
  | sdc item add --link-id 2 --text "Age" --type integer \
  | sdc validate
```

Extensions (SDC shortcuts and custom URLs):

```bash
sdc init --url http://example.org/q1 --title "My Form" \
  | sdc item add --link-id 1 --text "Name" --type string \
  | sdc extension add custom --link-id 1 \
      --url "http://example.org/ext" --value-string "hello" \
  | sdc validate
```

## Install options

| Install | Gets you |
|---|---|
| `pip install fhir-sdc-tools` | Python library + `sdc` CLI |
| `pip install fhir-sdc-tools[mcp]` | Above + `fhir-sdc-mcp` server with `render-questionnaire` tool |

## License

MIT
