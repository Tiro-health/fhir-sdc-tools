"""Pydantic models for FHIR SDC Questionnaire building."""

from __future__ import annotations

import os
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


# --- Enums ---


class FhirVersion(str, Enum):
    R4 = "R4"
    R5 = "R5"


# Profile URLs used to tag the questionnaire with its FHIR version
FHIR_VERSION_PROFILES: dict[FhirVersion, str] = {
    FhirVersion.R4: "http://hl7.org/fhir/4.0/StructureDefinition/Questionnaire",
    FhirVersion.R5: "http://hl7.org/fhir/5.0/StructureDefinition/Questionnaire",
}

# Reverse lookup: profile URL -> FhirVersion
_PROFILE_TO_VERSION: dict[str, FhirVersion] = {
    url: ver for ver, url in FHIR_VERSION_PROFILES.items()
}

# Item types available per FHIR version
_R4_ITEM_TYPES = {
    "group",
    "display",
    "boolean",
    "decimal",
    "integer",
    "date",
    "dateTime",
    "time",
    "string",
    "text",
    "url",
    "choice",
    "open-choice",
    "attachment",
    "reference",
    "quantity",
}

_R5_ONLY_ITEM_TYPES = {"coding", "question"}

ITEM_TYPES_FOR_VERSION: dict[FhirVersion, set[str]] = {
    FhirVersion.R4: _R4_ITEM_TYPES,
    FhirVersion.R5: _R4_ITEM_TYPES | _R5_ONLY_ITEM_TYPES,
}


class QuestionnaireItemType(str, Enum):
    GROUP = "group"
    DISPLAY = "display"
    BOOLEAN = "boolean"
    DECIMAL = "decimal"
    INTEGER = "integer"
    DATE = "date"
    DATE_TIME = "dateTime"
    TIME = "time"
    STRING = "string"
    TEXT = "text"
    URL = "url"
    CHOICE = "choice"
    OPEN_CHOICE = "open-choice"
    ATTACHMENT = "attachment"
    REFERENCE = "reference"
    QUANTITY = "quantity"
    # R5-only types
    CODING = "coding"
    QUESTION = "question"


class EnableWhenOperator(str, Enum):
    EXISTS = "exists"
    EQUALS = "="
    NOT_EQUALS = "!="
    GT = ">"
    LT = "<"
    GTE = ">="
    LTE = "<="


class PublicationStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    RETIRED = "retired"
    UNKNOWN = "unknown"


# --- SDC Extension URL Constants ---

SDC_BASE = "http://hl7.org/fhir/uv/sdc/StructureDefinition"
FHIR_BASE = "http://hl7.org/fhir/StructureDefinition"

TRANSLATION_URL = f"{FHIR_BASE}/translation"
ITEM_WEIGHT_URL = f"{FHIR_BASE}/itemWeight"

SDC_URLS: dict[str, str] = {
    "hidden": f"{FHIR_BASE}/questionnaire-hidden",
    "itemControl": f"{FHIR_BASE}/questionnaire-itemControl",
    "variable": f"{FHIR_BASE}/variable",
    "calculatedExpression": f"{SDC_BASE}/sdc-questionnaire-calculatedExpression",
    "initialExpression": f"{SDC_BASE}/sdc-questionnaire-initialExpression",
    "enableWhenExpression": f"{SDC_BASE}/sdc-questionnaire-enableWhenExpression",
    "candidateExpression": f"{SDC_BASE}/sdc-questionnaire-candidateExpression",
    "answerExpression": f"{SDC_BASE}/sdc-questionnaire-answerExpression",
}


# --- FHIR Models ---

_MODEL_CONFIG = ConfigDict(extra="allow", populate_by_name=True)


class Meta(BaseModel):
    model_config = _MODEL_CONFIG

    profile: list[str] | None = None


class Extension(BaseModel):
    model_config = _MODEL_CONFIG

    url: str


class EnableWhen(BaseModel):
    model_config = _MODEL_CONFIG

    question: str
    operator: EnableWhenOperator


class QuestionnaireItem(BaseModel):
    model_config = _MODEL_CONFIG

    link_id: str = Field(alias="linkId")
    definition: str | None = None
    text: str | None = None
    type: QuestionnaireItemType
    required: bool | None = None
    repeats: bool | None = None
    read_only: bool | None = Field(None, alias="readOnly")
    max_length: int | None = Field(None, alias="maxLength")
    enable_when: list[EnableWhen] | None = Field(None, alias="enableWhen")
    enable_behavior: str | None = Field(None, alias="enableBehavior")
    initial: list[dict[str, object]] | None = None
    answer_option: list[dict[str, object]] | None = Field(None, alias="answerOption")
    answer_value_set: str | None = Field(None, alias="answerValueSet")
    item: list[QuestionnaireItem] | None = None
    extension: list[Extension] | None = None


class Questionnaire(BaseModel):
    model_config = _MODEL_CONFIG

    resource_type: str = Field("Questionnaire", alias="resourceType")
    meta: Meta | None = None
    url: str | None = None
    title: str | None = None
    status: PublicationStatus = PublicationStatus.DRAFT
    name: str | None = None
    publisher: str | None = None
    description: str | None = None
    item: list[QuestionnaireItem] | None = None
    extension: list[Extension] | None = None

    @property
    def fhir_version(self) -> FhirVersion | None:
        """Detect FHIR version from meta.profile, or None if not set."""
        if self.meta and self.meta.profile:
            for profile_url in self.meta.profile:
                if profile_url in _PROFILE_TO_VERSION:
                    return _PROFILE_TO_VERSION[profile_url]
        return None


def resolve_fhir_version(q: Questionnaire | None = None) -> FhirVersion:
    """Resolve FHIR version: questionnaire meta.profile > env var > default R5."""
    if q is not None and q.fhir_version is not None:
        return q.fhir_version
    env = os.environ.get("SDC_FHIR_VERSION", "").upper()
    if env in ("R4", "R5"):
        return FhirVersion(env)
    return FhirVersion.R5


def set_fhir_version(q: Questionnaire, version: FhirVersion) -> Questionnaire:
    """Set the FHIR version in meta.profile. Returns new Questionnaire."""
    profile_url = FHIR_VERSION_PROFILES[version]
    existing_meta = q.meta or Meta()
    # Remove any existing version profiles, then add the new one
    profiles = [
        p for p in (existing_meta.profile or []) if p not in _PROFILE_TO_VERSION
    ]
    profiles.insert(0, profile_url)
    new_meta = existing_meta.model_copy(update={"profile": profiles})
    return q.model_copy(update={"meta": new_meta})
