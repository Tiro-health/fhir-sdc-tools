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
    "Tiro.health FHIR SDC tools": {
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
claude mcp add "Tiro.health FHIR SDC tools" -- uvx --from "fhir-sdc-tools[mcp]" fhir-sdc-mcp
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
q = set_fhir_version(q, FhirVersion.R5)
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

## Feedback & Issues

Found a bug or have a feature idea? Open an issue on GitHub:

- [Report a bug](https://github.com/Tiro-health/fhir-sdc-tools/issues/new?title=%5BBug%5D%3A+&body=%23%23+Description%0A%0A%23%23+Steps+to+reproduce%0A%0A1.+%0A2.+%0A3.+%0A%0A%23%23+Expected+behavior%0A%0A%23%23+Actual+behavior%0A%0A%23%23+Environment%0A%0A-+fhir-sdc-tools+version%3A+%0A-+Python+version%3A+%0A-+OS%3A+&labels=bug)
- [Request a feature](https://github.com/Tiro-health/fhir-sdc-tools/issues/new?title=%5BFeature%5D%3A+&body=%23%23+Description%0A%0A%23%23+Use+case%0A%0A%23%23+Proposed+solution%0A%0A&labels=enhancement)
- [Browse existing issues](https://github.com/Tiro-health/fhir-sdc-tools/issues)

## License

MIT
