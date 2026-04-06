"""Composable CLI for building FHIR SDC Questionnaires."""

from __future__ import annotations

import json
import sys

import click

from sdc.models import (
    EnableWhen,
    EnableWhenOperator,
    Extension,
    FhirVersion,
    PublicationStatus,
    Questionnaire,
    QuestionnaireItem,
    QuestionnaireItemType,
    SDC_URLS,
    resolve_fhir_version,
    set_fhir_version,
)
from sdc.transforms import (
    add_answer_option,
    add_enable_when,
    add_extension,
    add_item,
    add_translation,
    extract_texts,
    remove_extension,
    remove_item,
    set_answer_value_set,
    set_enable_behavior,
    set_meta,
    validate,
)


# --- IO Helpers ---


def read_stdin() -> Questionnaire:
    """Read a Questionnaire JSON from stdin."""
    if sys.stdin.isatty():
        raise click.UsageError(
            "No input on stdin. Pipe a questionnaire or use 'sdc init'."
        )
    data = json.loads(sys.stdin.read())
    return Questionnaire.model_validate(data)


def write_stdout(q: Questionnaire) -> None:
    """Write a Questionnaire as JSON to stdout."""
    click.echo(q.model_dump_json(by_alias=True, exclude_none=True, indent=2))


# --- CLI ---

MAIN_EPILOG = """
All commands (except init) read JSON from stdin and write to stdout.
Chain them with pipes to build questionnaires incrementally.

\b
  sdc init --url http://example.org/q1 --title "My Form" \\
    | sdc item add --link-id 1 --text "Name" --type string \\
    | sdc item add --link-id 2 --text "Has allergy?" --type boolean \\
    | sdc enable-when add --link-id 2 --question 1 --operator exists \\
    | sdc validate

\b
Environment:
  SDC_FHIR_VERSION   Set default FHIR version (R4 or R5)
"""


CONTEXT_SETTINGS = {"max_content_width": 120}


@click.group(epilog=MAIN_EPILOG, context_settings=CONTEXT_SETTINGS)
def cli() -> None:
    """Composable CLI for building FHIR SDC Questionnaires."""


# --- init ---

INIT_EPILOG = """
\b
Examples:
  sdc init --url http://example.org/q1 --title "Intake Form"
  sdc init --url http://example.org/q1 --title "R5 Form" --fhir-version R5
  SDC_FHIR_VERSION=R5 sdc init --url http://example.org/q1 --title "R5 Form"
"""


@cli.command(epilog=INIT_EPILOG)
@click.option("--url", required=True, help="Canonical URL for the questionnaire.")
@click.option("--title", required=True, help="Human-readable title.")
@click.option(
    "--status",
    type=click.Choice([s.value for s in PublicationStatus]),
    default="draft",
    help="Publication status.",
)
@click.option("--name", default=None, help="Computer-friendly name.")
@click.option(
    "--fhir-version",
    "fhir_version",
    type=click.Choice(["R4", "R5"], case_sensitive=False),
    default=None,
    help="FHIR version (R4 or R5). Falls back to SDC_FHIR_VERSION env var, then R4.",
)
def init(
    url: str,
    title: str,
    status: str,
    name: str | None,
    fhir_version: str | None,
) -> None:
    """Create a new empty Questionnaire."""
    q = Questionnaire(
        url=url,
        title=title,
        status=PublicationStatus(status),
        name=name,
    )
    version = (
        FhirVersion(fhir_version.upper()) if fhir_version else resolve_fhir_version()
    )
    q = set_fhir_version(q, version)
    write_stdout(q)


# --- item ---

ITEM_ADD_EPILOG = """
\b
Examples:
  sdc item add --link-id 1 --text "Full name" --type string --required
  sdc item add --link-id grp --text "Section" --type group
  sdc item add --link-id 1.1 --text "First name" --type string --parent grp
  sdc item add --link-id bp --text "Blood pressure" --type quantity --repeats
\b
  With definition (for SDC extraction):
  sdc item add --link-id name --text "Name" --type group --repeats \\
    --definition "http://hl7.org/fhir/StructureDefinition/Patient#Patient.name"
\b
Item types:
  R4: group, display, boolean, decimal, integer, date, dateTime, time,
      string, text, url, choice, open-choice, attachment, reference, quantity
  R5: replaces choice/open-choice with 'coding', adds 'question'
"""


@cli.group()
def item() -> None:
    """Add or remove questionnaire items."""


@item.command("add", epilog=ITEM_ADD_EPILOG)
@click.option("--link-id", "link_id", required=True, help="Unique linkId.")
@click.option("--text", default=None, help="Display text.")
@click.option(
    "--type",
    "item_type",
    required=True,
    type=click.Choice([t.value for t in QuestionnaireItemType]),
    help="Item type (R4: choice/open-choice, R5: coding).",
)
@click.option(
    "--parent", default=None, help="Parent linkId to nest under (must exist)."
)
@click.option("--required", "is_required", is_flag=True, help="Mark as required.")
@click.option("--repeats", is_flag=True, help="Allow repeating answers.")
@click.option(
    "--definition",
    default=None,
    help="Element definition URI for SDC extraction (e.g. ...Patient#Patient.name).",
)
def item_add(
    link_id: str,
    text: str | None,
    item_type: str,
    parent: str | None,
    is_required: bool,
    repeats: bool,
    definition: str | None,
) -> None:
    """Add an item to the questionnaire."""
    q = read_stdin()
    new_item = QuestionnaireItem(
        link_id=link_id,
        text=text,
        type=QuestionnaireItemType(item_type),
        required=is_required or None,
        repeats=repeats or None,
        definition=definition,
    )
    q = add_item(q, new_item, parent)
    write_stdout(q)


ITEM_REMOVE_EPILOG = """
\b
Examples:
  sdc item remove --link-id 2
  sdc item remove --link-id nested.1   # removes from anywhere in the tree
"""


@item.command("remove", epilog=ITEM_REMOVE_EPILOG)
@click.option("--link-id", "link_id", required=True, help="linkId to remove.")
def item_remove(link_id: str) -> None:
    """Remove an item by linkId (searches the entire tree)."""
    q = read_stdin()
    q = remove_item(q, link_id)
    write_stdout(q)


# --- enable-when ---

ENABLE_WHEN_ADD_EPILOG = """
Provide exactly one --answer-* flag matching the source question's type.

\b
Examples:
  sdc enable-when add --link-id 2 --question 1 --operator = --answer-boolean true
  sdc enable-when add --link-id 3 --question 2 --operator != --answer-string "No"
  sdc enable-when add --link-id 4 --question 3 --operator exists --answer-boolean true
  sdc enable-when add --link-id 5 --question 4 --operator = \\
    --answer-coding "http://snomed.info/sct|73211009|Diabetes mellitus"
"""


@cli.group("enable-when")
def enable_when_group() -> None:
    """Manage enableWhen conditions on items."""


@enable_when_group.command("add", epilog=ENABLE_WHEN_ADD_EPILOG)
@click.option("--link-id", "link_id", required=True, help="Target item linkId.")
@click.option("--question", required=True, help="Source question linkId.")
@click.option(
    "--operator",
    required=True,
    type=click.Choice([o.value for o in EnableWhenOperator]),
    help="Comparison operator.",
)
@click.option("--answer-boolean", type=bool, default=None, help="Boolean answer.")
@click.option("--answer-string", default=None, help="String answer.")
@click.option("--answer-integer", type=int, default=None, help="Integer answer.")
@click.option(
    "--answer-coding",
    default=None,
    help="Coding as 'system|code|display' (display optional).",
)
def enable_when_add(
    link_id: str,
    question: str,
    operator: str,
    answer_boolean: bool | None,
    answer_string: str | None,
    answer_integer: int | None,
    answer_coding: str | None,
) -> None:
    """Add an enableWhen condition to an item."""
    q = read_stdin()

    ew_data: dict[str, object] = {
        "question": question,
        "operator": operator,
    }

    if answer_boolean is not None:
        ew_data["answerBoolean"] = answer_boolean
    elif answer_string is not None:
        ew_data["answerString"] = answer_string
    elif answer_integer is not None:
        ew_data["answerInteger"] = answer_integer
    elif answer_coding is not None:
        parts = answer_coding.split("|")
        coding: dict[str, str] = {"system": parts[0], "code": parts[1]}
        if len(parts) > 2:
            coding["display"] = parts[2]
        ew_data["answerCoding"] = coding

    ew = EnableWhen.model_validate(ew_data)
    q = add_enable_when(q, link_id, ew)
    write_stdout(q)


ENABLE_WHEN_BEHAVIOR_EPILOG = """
Required when an item has multiple enableWhen conditions.

\b
Examples:
  sdc enable-when set-behavior --link-id 2 --behavior all   # all must match
  sdc enable-when set-behavior --link-id 2 --behavior any   # any can match
"""


@enable_when_group.command("set-behavior", epilog=ENABLE_WHEN_BEHAVIOR_EPILOG)
@click.option("--link-id", "link_id", required=True, help="Target item linkId.")
@click.option(
    "--behavior",
    required=True,
    type=click.Choice(["all", "any"]),
    help="Enable behavior.",
)
def enable_when_set_behavior(link_id: str, behavior: str) -> None:
    """Set enableBehavior (all/any) on an item."""
    q = read_stdin()
    q = set_enable_behavior(q, link_id, behavior)
    write_stdout(q)


# --- answer-option ---

ANSWER_OPTION_ADD_EPILOG = """
Provide exactly one --value-* flag per invocation. Pipe multiple times
to add several options.

\b
Coding format: system|code[|display]  (display is optional)
\b
Examples:
  sdc answer-option add --link-id 1 --value-string "Option A"
  sdc answer-option add --link-id 1 --value-integer 42
  sdc answer-option add --link-id 1 \\
    --value-coding "http://snomed.info/sct|73211009|Diabetes mellitus"
"""


@cli.group("answer-option")
def answer_option_group() -> None:
    """Manage answer options on choice/coding items."""


@answer_option_group.command("add", epilog=ANSWER_OPTION_ADD_EPILOG)
@click.option("--link-id", "link_id", required=True, help="Target item linkId.")
@click.option("--value-string", default=None, help="String option value.")
@click.option("--value-integer", type=int, default=None, help="Integer option value.")
@click.option(
    "--value-coding",
    default=None,
    help="Coding as 'system|code|display' (display optional).",
)
def answer_option_add(
    link_id: str,
    value_string: str | None,
    value_integer: int | None,
    value_coding: str | None,
) -> None:
    """Add an answer option to an item."""
    q = read_stdin()

    option: dict[str, object] = {}
    if value_string is not None:
        option["valueString"] = value_string
    elif value_integer is not None:
        option["valueInteger"] = value_integer
    elif value_coding is not None:
        parts = value_coding.split("|")
        coding: dict[str, str] = {"system": parts[0], "code": parts[1]}
        if len(parts) > 2:
            coding["display"] = parts[2]
        option["valueCoding"] = coding
    else:
        raise click.UsageError(
            "Provide --value-string, --value-integer, or --value-coding."
        )

    q = add_answer_option(q, link_id, option)
    write_stdout(q)


ANSWER_OPTION_VS_EPILOG = """
\b
Examples:
  sdc answer-option set-value-set --link-id 1 \\
    --url "http://hl7.org/fhir/ValueSet/administrative-gender"
"""


@answer_option_group.command("set-value-set", epilog=ANSWER_OPTION_VS_EPILOG)
@click.option("--link-id", "link_id", required=True, help="Target item linkId.")
@click.option("--url", required=True, help="ValueSet canonical URL.")
def answer_option_set_value_set(link_id: str, url: str) -> None:
    """Set answerValueSet on an item (alternative to inline answer options)."""
    q = read_stdin()
    q = set_answer_value_set(q, link_id, url)
    write_stdout(q)


# --- extension ---

EXTENSION_ADD_EPILOG = """
Use --name for common SDC extensions (resolves the full URL automatically),
or --url for any arbitrary extension. Omit --link-id to add at the
questionnaire level.

\b
SDC shorthands and typical usage:
  hidden               --value-boolean true
  itemControl          --value-code drop-down
  variable             --expression "..." [--description "..."]
  calculatedExpression --expression "..."
  initialExpression    --expression "..."
  enableWhenExpression --expression "..."
  candidateExpression  --expression "..."
  answerExpression     --expression "..."
\b
Examples:
  sdc extension add --link-id 1 --name hidden --value-boolean true
  sdc extension add --link-id 1 --name itemControl --value-code drop-down
  sdc extension add --name variable \\
    --expression "%resource.item.where(linkId='weight').answer.value" \\
    --description "weight"
  sdc extension add --link-id bmi --name calculatedExpression \\
    --expression "%weight / (%height / 100).power(2)"
  sdc extension add --url "http://custom.org/ext" --value-string "hello"
"""


@cli.group()
def extension() -> None:
    """Add or remove extensions (SDC shorthands or arbitrary URLs)."""


@extension.command("add", epilog=EXTENSION_ADD_EPILOG)
@click.option(
    "--link-id",
    "link_id",
    default=None,
    help="Target item linkId (omit for questionnaire-level).",
)
@click.option(
    "--name",
    "ext_name",
    default=None,
    help=f"SDC shorthand: {', '.join(SDC_URLS)}.",
)
@click.option(
    "--url",
    "ext_url",
    default=None,
    help="Full extension URL (alternative to --name).",
)
@click.option("--value-boolean", type=bool, default=None, help="Boolean value.")
@click.option("--value-string", default=None, help="String value.")
@click.option(
    "--value-code", default=None, help="Code value (wrapped in CodeableConcept)."
)
@click.option("--value-integer", type=int, default=None, help="Integer value.")
@click.option("--expression", default=None, help="FHIRPath expression.")
@click.option(
    "--language",
    default="text/fhirpath",
    help="Expression language (default: text/fhirpath).",
)
@click.option(
    "--description", "expr_description", default=None, help="Expression description."
)
def extension_add(
    link_id: str | None,
    ext_name: str | None,
    ext_url: str | None,
    value_boolean: bool | None,
    value_string: str | None,
    value_code: str | None,
    value_integer: int | None,
    expression: str | None,
    language: str,
    expr_description: str | None,
) -> None:
    """Add an extension to an item or questionnaire."""
    q = read_stdin()

    # Resolve URL
    if ext_name and ext_url:
        raise click.UsageError("Use --name or --url, not both.")
    if ext_name:
        if ext_name not in SDC_URLS:
            raise click.UsageError(
                f"Unknown extension name '{ext_name}'. Known: {', '.join(SDC_URLS)}."
            )
        url = SDC_URLS[ext_name]
    elif ext_url:
        url = ext_url
    else:
        raise click.UsageError("Provide --name or --url.")

    # Build extension data
    ext_data: dict[str, object] = {"url": url}

    if expression is not None:
        expr_obj: dict[str, str] = {
            "language": language,
            "expression": expression,
        }
        if expr_description:
            expr_obj["description"] = expr_description
        ext_data["valueExpression"] = expr_obj
    elif value_boolean is not None:
        ext_data["valueBoolean"] = value_boolean
    elif value_string is not None:
        ext_data["valueString"] = value_string
    elif value_code is not None:
        ext_data["valueCodeableConcept"] = {
            "coding": [{"code": value_code}],
        }
    elif value_integer is not None:
        ext_data["valueInteger"] = value_integer
    else:
        raise click.UsageError(
            "Provide a value flag (--value-boolean, --value-string, --value-code, --expression, etc.)."
        )

    ext = Extension.model_validate(ext_data)
    q = add_extension(q, ext, link_id)
    write_stdout(q)


EXTENSION_REMOVE_EPILOG = """
\b
Examples:
  sdc extension remove --link-id 1 --name hidden
  sdc extension remove --url "http://custom.org/ext"
  sdc extension remove --name variable        # questionnaire-level
"""


@extension.command("remove", epilog=EXTENSION_REMOVE_EPILOG)
@click.option(
    "--link-id",
    "link_id",
    default=None,
    help="Target item linkId (omit for questionnaire-level).",
)
@click.option("--name", "ext_name", default=None, help="SDC shorthand name.")
@click.option("--url", "ext_url", default=None, help="Full extension URL.")
def extension_remove(
    link_id: str | None,
    ext_name: str | None,
    ext_url: str | None,
) -> None:
    """Remove all extensions matching the URL from an item or questionnaire."""
    if ext_name and ext_url:
        raise click.UsageError("Use --name or --url, not both.")
    if ext_name:
        if ext_name not in SDC_URLS:
            raise click.UsageError(f"Unknown extension name '{ext_name}'.")
        url = SDC_URLS[ext_name]
    elif ext_url:
        url = ext_url
    else:
        raise click.UsageError("Provide --name or --url.")

    q = read_stdin()
    q = remove_extension(q, url, link_id)
    write_stdout(q)


# --- meta ---

META_EPILOG = """
\b
Examples:
  sdc meta --status active --publisher "My Org"
  sdc meta --language en --description "Patient intake form"
"""


@cli.command(epilog=META_EPILOG)
@click.option(
    "--status",
    default=None,
    type=click.Choice([s.value for s in PublicationStatus]),
    help="Publication status.",
)
@click.option("--publisher", default=None, help="Publisher name.")
@click.option("--description", default=None, help="Description.")
@click.option("--name", default=None, help="Computer-friendly name.")
@click.option("--title", default=None, help="Human-readable title.")
@click.option("--url", default=None, help="Canonical URL.")
@click.option("--language", default=None, help="Base language (BCP-47 code, e.g. en).")
def meta(
    status: str | None,
    publisher: str | None,
    description: str | None,
    name: str | None,
    title: str | None,
    url: str | None,
    language: str | None,
) -> None:
    """Set top-level metadata fields."""
    q = read_stdin()
    fields: dict[str, object] = {}
    if status is not None:
        fields["status"] = PublicationStatus(status)
    if publisher is not None:
        fields["publisher"] = publisher
    if description is not None:
        fields["description"] = description
    if name is not None:
        fields["name"] = name
    if title is not None:
        fields["title"] = title
    if url is not None:
        fields["url"] = url
    if language is not None:
        fields["language"] = language
    if not fields:
        raise click.UsageError("Provide at least one field to set.")
    q = set_meta(q, **fields)
    write_stdout(q)


# --- validate ---

VALIDATE_EPILOG = """
Checks: unique linkIds, enableWhen references, item types vs FHIR version.
Warnings go to stderr so the JSON pipeline is not interrupted.

\b
Examples:
  sdc init ... | sdc item add ... | sdc validate
  sdc validate < questionnaire.json > validated.json
"""


@cli.command("validate", epilog=VALIDATE_EPILOG)
def validate_cmd() -> None:
    """Validate structure and pass through. Warnings to stderr, JSON to stdout."""
    q = read_stdin()
    warnings = validate(q)
    for w in warnings:
        click.echo(f"WARNING: {w}", err=True)
    write_stdout(q)


# --- translate ---

TRANSLATE_EPILOG = """
Adds FHIR translation extensions to primitive string fields using the
standard _ prefix companion property (_text, _title, _display, etc.).

\b
Modes:
  --link-id only           Translate item text
  --link-id + --answer-code  Translate answer option display (by code)
  --link-id + --answer-index Translate answer option (by 0-based index)
  --field                  Translate questionnaire-level title/description
\b
Examples:
  sdc translate --link-id 1 --lang nl --value "Wat is uw naam?"
  sdc translate --link-id 1 --lang fr --value "Quel est votre nom?"
  sdc translate --field title --lang nl --value "Inname"
  sdc translate --link-id 2 --answer-code male --lang nl --value "Man"
  sdc translate --link-id 2 --answer-index 0 --lang nl --value "Optie A"
"""


@cli.command(epilog=TRANSLATE_EPILOG)
@click.option(
    "--link-id",
    "link_id",
    default=None,
    help="Target item linkId (translates 'text', or use with --answer-*).",
)
@click.option(
    "--field",
    default=None,
    type=click.Choice(["title", "description"]),
    help="Questionnaire-level field to translate.",
)
@click.option(
    "--answer-code",
    default=None,
    help="Translate answer option matching this valueCoding.code.",
)
@click.option(
    "--answer-index",
    type=int,
    default=None,
    help="Translate answer option at this 0-based index.",
)
@click.option("--lang", required=True, help="BCP-47 language code (e.g. nl, fr, de).")
@click.option("--value", required=True, help="Translated text.")
def translate(
    link_id: str | None,
    field: str | None,
    answer_code: str | None,
    answer_index: int | None,
    lang: str,
    value: str,
) -> None:
    """Add a FHIR translation extension to an item or questionnaire field."""
    if field and link_id:
        raise click.UsageError("Use --link-id or --field, not both.")
    if not field and not link_id:
        raise click.UsageError(
            "Provide --link-id (for item text / answer options) or --field (for title/description)."
        )
    if answer_code is not None and answer_index is not None:
        raise click.UsageError("Use --answer-code or --answer-index, not both.")
    if (answer_code is not None or answer_index is not None) and not link_id:
        raise click.UsageError("--answer-code/--answer-index require --link-id.")

    q = read_stdin()
    q = add_translation(
        q,
        lang,
        value,
        link_id=link_id,
        field=field,
        answer_code=answer_code,
        answer_index=answer_index,
    )
    write_stdout(q)


# --- extract-texts ---

EXTRACT_TEXTS_EPILOG = """
Extracts all translatable strings to CSV. Add empty columns for target
languages, fill them in, then use apply-translations to apply.

\b
Examples:
  sdc extract-texts < questionnaire.json > texts.csv
  sdc extract-texts --langs fr,en < questionnaire.json > texts.csv
"""


@cli.command("extract-texts", epilog=EXTRACT_TEXTS_EPILOG)
@click.option(
    "--langs",
    default="",
    help="Comma-separated target language codes to add as empty columns (e.g. fr,en).",
)
def extract_texts_cmd(langs: str) -> None:
    """Extract all translatable strings to CSV."""
    import csv
    import io

    q = read_stdin()
    rows = extract_texts(q)

    lang_cols = [col.strip() for col in langs.split(",") if col.strip()]
    fieldnames = ["linkId", "field", "answer_code", "answer_index", "text"] + lang_cols

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        for lang in lang_cols:
            row[lang] = ""
        writer.writerow(row)

    click.echo(output.getvalue(), nl=False)


# --- apply-translations ---

APPLY_TRANSLATIONS_EPILOG = """
Reads a CSV file with translations and applies them to the questionnaire.
The CSV must have columns: linkId, field, answer_code, answer_index, text,
plus a column for each target language.

\b
Examples:
  sdc apply-translations --csv texts.csv --lang fr < q.json > q_fr.json
  cat q.json \\
    | sdc apply-translations --csv texts.csv --lang fr \\
    | sdc apply-translations --csv texts.csv --lang en \\
    > q_translated.json
"""


@cli.command("apply-translations", epilog=APPLY_TRANSLATIONS_EPILOG)
@click.option("--csv-file", "csv_path", required=True, help="Path to translations CSV.")
@click.option("--lang", required=True, help="Target language column to apply.")
def apply_translations_cmd(csv_path: str, lang: str) -> None:
    """Apply translations from a CSV file to a questionnaire."""
    import csv

    q = read_stdin()

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if lang not in (reader.fieldnames or []):
            raise click.UsageError(f"Column '{lang}' not found in CSV.")

        for row in reader:
            value = row.get(lang, "").strip()
            if not value:
                continue

            link_id = row.get("linkId", "").strip() or None
            field = row.get("field", "").strip()
            answer_code = row.get("answer_code", "").strip() or None
            answer_index_str = row.get("answer_index", "").strip()
            answer_index = (
                int(answer_index_str)
                if answer_index_str and field == "answer" and not answer_code
                else None
            )

            if field in ("name", "title", "description"):
                q = add_translation(q, lang, value, field=field)
            elif field == "text" and link_id:
                q = add_translation(q, lang, value, link_id=link_id)
            elif field == "answer" and link_id and answer_code:
                q = add_translation(
                    q, lang, value, link_id=link_id, answer_code=answer_code
                )
            elif field == "answer" and link_id and answer_index is not None:
                q = add_translation(
                    q, lang, value, link_id=link_id, answer_index=answer_index
                )

    write_stdout(q)
