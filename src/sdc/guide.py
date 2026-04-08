"""Built-in guide content for ``sdc guide``."""

from __future__ import annotations

OVERVIEW = """\
SDC — Composable CLI for building FHIR SDC Questionnaires

PIPE PATTERN
  All commands (except init) read JSON from stdin and write to stdout.
  Chain them with pipes to build questionnaires incrementally:

    sdc init --url http://example.org/q1 --title "My Form" \\
      | sdc item add --link-id name --text "Full name" --type string --required \\
      | sdc item add --link-id dob --text "Date of birth" --type date \\
      | sdc validate

COMMANDS
  init                    Create a new empty Questionnaire
  item add                Add an item (question, group, display)
  item remove             Remove an item by linkId
  enable-when add         Add conditional display logic
  enable-when set-behavior  Set all/any for multiple conditions
  answer-option add       Add an answer option to a choice item
  answer-option set-value-set  Bind to an external ValueSet
  extension add           Add an SDC extension (or arbitrary extension)
  extension remove        Remove extensions by URL or shorthand
  meta                    Set top-level metadata fields
  validate                Validate structure (warnings to stderr)
  translate               Add a FHIR translation extension
  extract-texts           Extract translatable strings to CSV
  apply-translations      Apply translations from a CSV file
  guide [TOPIC]           Show this guide

ENVIRONMENT
  SDC_FHIR_VERSION        Set default FHIR version (R4 or R5)

TOPICS
  sdc guide               This overview
  sdc guide examples      Complete pipeline examples
  sdc guide extensions    SDC extension shorthands and expressions
  sdc guide fhir          FHIR R4 vs R5 differences
  sdc guide api           Python API quick reference
"""

EXAMPLES = """\
EXAMPLES — Complete pipeline recipes

1. INTAKE FORM
   A simple form with text fields and a coded choice:

    sdc init --url http://example.org/intake --title "Intake Form" \\
      | sdc item add --link-id name --text "Full name" --type string --required \\
      | sdc item add --link-id dob --text "Date of birth" --type date --required \\
      | sdc item add --link-id gender --text "Gender" --type choice \\
      | sdc answer-option add --link-id gender \\
          --value-coding "http://hl7.org/fhir/administrative-gender|male|Male" \\
      | sdc answer-option add --link-id gender \\
          --value-coding "http://hl7.org/fhir/administrative-gender|female|Female" \\
      | sdc extension add --link-id gender --name itemControl --value-code drop-down \\
      | sdc validate \\
      | tee intake.json

2. BMI CALCULATOR WITH VARIABLES
   Uses FHIRPath variables and a calculated expression:

    sdc init --url http://example.org/bmi --title "BMI Calculator" \\
      | sdc item add --link-id grp --text "BMI Calculator" --type group \\
      | sdc extension add --link-id grp --name variable \\
          --expression "QuestionnaireResponse.item.where(linkId='weight').answer.value" \\
          --description weight \\
      | sdc extension add --link-id grp --name variable \\
          --expression "QuestionnaireResponse.item.where(linkId='height').answer.value" \\
          --description height \\
      | sdc extension add --link-id grp --name variable \\
          --expression "iif(%weight.exists() and %height > 0, (%weight / (%height / 100).power(2)).round(1), {})" \\
          --description bmi \\
      | sdc item add --link-id weight --text "Weight (kg)" --type decimal --required --parent grp \\
      | sdc item add --link-id height --text "Height (cm)" --type decimal --required --parent grp \\
      | sdc item add --link-id bmi-result --text "Your BMI" --type decimal --parent grp \\
      | sdc extension add --link-id bmi-result --name calculatedExpression \\
          --expression "%bmi" \\
      | sdc validate \\
      | tee bmi.json

3. CONDITIONAL DISPLAY
   Show a follow-up question only when a boolean is true:

    sdc init --url http://example.org/allergy --title "Allergy Check" \\
      | sdc item add --link-id has-allergy --text "Do you have allergies?" --type boolean \\
      | sdc item add --link-id allergy-detail --text "Please describe" --type text \\
      | sdc enable-when add --link-id allergy-detail \\
          --question has-allergy --operator = --answer-boolean true \\
      | sdc validate

4. TRANSLATION WORKFLOW
   Extract strings, translate, and apply:

    sdc extract-texts --langs nl,fr < questionnaire.json > texts.csv
    # ... fill in the nl and fr columns in texts.csv ...
    cat questionnaire.json \\
      | sdc apply-translations --csv-file texts.csv --lang nl \\
      | sdc apply-translations --csv-file texts.csv --lang fr \\
      > questionnaire_translated.json

   Or translate individual items inline:

    cat questionnaire.json \\
      | sdc translate --link-id name --lang nl --value "Volledige naam" \\
      | sdc translate --link-id dob --lang nl --value "Geboortedatum" \\
      > questionnaire_nl.json

5. MODIFYING AN EXISTING QUESTIONNAIRE
   Read from a file, add items, and write back:

    cat existing.json \\
      | sdc item add --link-id new-q --text "New question" --type string \\
      | sdc extension add --link-id new-q --name hidden --value-boolean true \\
      | sdc validate \\
      > updated.json
"""


def _build_extensions_topic() -> str:
    """Build the extensions topic dynamically from SDC_URLS."""
    from sdc.models import SDC_URLS

    lines = [
        "EXTENSIONS — SDC extension shorthands and expression patterns",
        "",
        "SHORTHANDS",
        "  Use --name SHORTHAND instead of the full extension URL.",
        "  The following shorthands are recognized:",
        "",
    ]
    # Find the longest shorthand name for alignment
    max_len = max(len(name) for name in SDC_URLS)
    for name, url in SDC_URLS.items():
        lines.append(f"    {name:<{max_len}}  {url}")

    lines += [
        "",
        "USAGE PATTERNS",
        "",
        "  Hide an item:",
        "    sdc extension add --link-id ID --name hidden --value-boolean true",
        "",
        "  Set item control (drop-down, radio-button, check-box, etc.):",
        "    sdc extension add --link-id ID --name itemControl --value-code drop-down",
        "",
        "  Define a FHIRPath variable on a group:",
        "    sdc extension add --link-id GRP --name variable \\",
        '        --expression "QuestionnaireResponse.item.where(linkId=\'weight\').answer.value" \\',
        "        --description weight",
        "",
        "  Calculated expression (auto-fill from variables):",
        '    sdc extension add --link-id ID --name calculatedExpression --expression "%bmi"',
        "",
        "  Initial expression (pre-populate on load):",
        "    sdc extension add --link-id ID --name initialExpression \\",
        "        --expression \"Patient.name.first().given.first()\"",
        "",
        "  Enable-when expression (FHIRPath alternative to enable-when):",
        "    sdc extension add --link-id ID --name enableWhenExpression \\",
        "        --expression \"%age >= 18\"",
        "",
        "  Candidate expression (dynamic answer list):",
        "    sdc extension add --link-id ID --name candidateExpression \\",
        "        --expression \"Condition.code.coding\"",
        "",
        "  Answer expression (bind answers to a FHIRPath result):",
        "    sdc extension add --link-id ID --name answerExpression \\",
        "        --expression \"Practitioner.name\"",
        "",
        "  Arbitrary extension by URL:",
        "    sdc extension add --link-id ID \\",
        "        --url http://hl7.org/fhir/StructureDefinition/my-ext \\",
        "        --value-string \"custom value\"",
        "",
        "  Remove extensions:",
        "    sdc extension remove --link-id ID --name hidden",
        "    sdc extension remove --link-id ID --url http://full/url",
        "",
    ]
    return "\n".join(lines)


FHIR_NOTES = """\
FHIR VERSION NOTES — R4 vs R5 differences

ITEM TYPES
  R4: group, display, boolean, decimal, integer, date, dateTime, time,
      string, text, url, choice, open-choice, attachment, reference, quantity
  R5: Replaces choice/open-choice with 'coding'. Adds 'question' type.

SETTING THE VERSION
  CLI flag (on init):
    sdc init --url URL --title TITLE --fhir-version R5

  Environment variable (applies to all commands):
    export SDC_FHIR_VERSION=R5

  Python API:
    from sdc import set_fhir_version, FhirVersion
    q = set_fhir_version(q, FhirVersion.R5)

  Precedence: --fhir-version flag > SDC_FHIR_VERSION env var > R4 default

WHEN TO USE R5
  The Tiro Health renderer defaults to R5. If you are previewing
  questionnaires with the render-questionnaire MCP tool, use R5 to
  ensure item types are interpreted correctly.

MIGRATION
  If you have an R4 questionnaire with choice/open-choice items,
  switching to R5 will cause validate to warn about unknown item types.
  Replace 'choice' with 'coding' and remove 'open-choice' items.
"""

API_REF = """\
PYTHON API — Quick reference

IMPORTS
    from sdc import (
        Questionnaire, QuestionnaireItem, QuestionnaireItemType,
        EnableWhen, EnableWhenOperator, Extension,
        FhirVersion, SDC_URLS,
        add_item, remove_item, find_item,
        add_enable_when, set_enable_behavior,
        add_answer_option, set_answer_value_set,
        add_extension, remove_extension,
        set_meta, validate,
        add_translation, extract_texts,
        set_fhir_version, resolve_fhir_version,
    )

CREATING A QUESTIONNAIRE
    q = Questionnaire(url="http://example.org/q", title="My Form")
    q = set_fhir_version(q, FhirVersion.R4)

ADDING ITEMS
    item = QuestionnaireItem(
        link_id="name", text="Full name", type=QuestionnaireItemType.STRING
    )
    q = add_item(q, item)
    q = add_item(q, child_item, parent_link_id="group1")  # nested

ANSWER OPTIONS
    q = add_answer_option(q, "gender", value_coding={"system": "...", "code": "M"})
    q = set_answer_value_set(q, "gender", "http://example.org/ValueSet/gender")

EXTENSIONS
    q = add_extension(q, Extension(url=SDC_URLS["hidden"], value_boolean=True), "item1")
    q = remove_extension(q, SDC_URLS["hidden"], "item1")

CONDITIONAL DISPLAY
    ew = EnableWhen(question="q1", operator=EnableWhenOperator.EQUAL, answer_boolean=True)
    q = add_enable_when(q, "q2", ew)
    q = set_enable_behavior(q, "q2", "all")

VALIDATION
    warnings = validate(q)
    for w in warnings:
        print(f"WARNING: {w}")

SERIALIZATION
    # Always use by_alias and exclude_none for valid FHIR JSON:
    json_str = q.model_dump_json(by_alias=True, exclude_none=True, indent=2)

IMMUTABILITY
    All transform functions return a new Questionnaire. Chain by reassigning:
    q = add_item(q, item1)
    q = add_item(q, item2)
    q = validate(q)  # returns warnings, not a new questionnaire
"""


# Topic registry: name -> (short description, content)
TOPICS: dict[str, tuple[str, str]] = {
    "overview": ("Command summary and quick reference", OVERVIEW),
    "examples": ("Complete pipeline examples", EXAMPLES),
    "extensions": ("SDC extension shorthands and expressions", ""),  # built lazily
    "fhir": ("FHIR R4 vs R5 differences", FHIR_NOTES),
    "api": ("Python API quick reference", API_REF),
}

DEFAULT_TOPIC = "overview"


def get_topic(name: str) -> tuple[str, str] | None:
    """Return (description, content) for a topic, or None if not found."""
    if name not in TOPICS:
        return None
    description, content = TOPICS[name]
    if name == "extensions" and not content:
        content = _build_extensions_topic()
        TOPICS[name] = (description, content)
    return description, content
