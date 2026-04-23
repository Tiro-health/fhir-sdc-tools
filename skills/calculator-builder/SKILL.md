---
name: calculator-builder
description: >
  Build clinical risk calculators and scoring tools as FHIR SDC Questionnaires.
  Use this skill whenever the user wants to create a clinical calculator, risk score,
  staging system, prognostic index, or any tool that takes clinical inputs and computes
  a score or classification. Triggers on mentions of specific scores (e.g. "DIPSS",
  "CHA2DS2-VASc", "HCT-CI", "IPSS-M", "TNM", "Glasgow", "SOFA", "APACHE", "Wells",
  "Framingham", "MELD", "Child-Pugh"), or general phrases like "build a calculator",
  "make a scoring tool", "risk stratification form", "prognostic score", or
  "clinical decision support". Also use when the user wants to convert a published
  scoring system into a FHIR Questionnaire.
---

# Calculator builder

This skill guides you through building clinical calculators as FHIR SDC Questionnaires. It complements the `sdc-builder` skill — read that skill first for CLI/API reference, then come back here for calculator-specific architecture.

## Workflow

1. **Research** the scoring system — find the published source, all input variables, scoring logic, risk categories, and outcome data
2. **Classify** the calculator into one of three types (see below)
3. **Build** the questionnaire using the appropriate pattern for that type
4. **Validate and render** using `sdc validate` and the Tiro renderer

Always research thoroughly before building. Clinical calculators must be accurate — wrong coefficients or cutoffs can lead to clinical harm. Cross-reference multiple sources (original publication, MDCalc, UpToDate) and prefer the primary literature or open-source reference implementations (e.g. GitHub repos from the authors) for exact values.

---

## The three calculator types

Every clinical calculator falls into one of three types based on how inputs are combined into outputs. Identifying the type first determines which FHIR pattern to use.

### Type 1: Weight-based

Each question contributes a fixed numeric weight, and the total score is the sum of all weights. This is the most common type.

**When to use:** The scoring system assigns points to discrete options, and the final score is a simple sum. Different options for the same question may carry different weights (e.g. age <65 = 0, 65-74 = 1, ≥75 = 2).

**Examples:** CHA₂DS₂-VASc, HAS-BLED, DIPSS, HCT-CI, Wells score, Child-Pugh, Glasgow Coma Scale, SOFA, APACHE II

**FHIR pattern:** Use `itemWeight` extension on answer options + `weight().sum()` in a calculated expression.

### Type 2: Formula-based

Questions collect numeric values that are combined through a mathematical formula — multiplication by coefficients, division, exponents, or other transformations.

**When to use:** The scoring system uses continuous variables with regression coefficients, or mathematical transformations like ratios, products, or logarithmic scales.

**Examples:** IPSS-M, BMI, MELD score, Framingham risk score, CKD-EPI eGFR, SOKAL, EuroSCORE II

**FHIR pattern:** Use `variable` extensions for intermediate computations + `calculatedExpression` for the final result.

### Type 3: Discrete logic

Multiple categorical or boolean inputs are combined through decision-tree logic (not arithmetic) to produce a categorical output. There is no meaningful numeric score — the output is a classification.

**When to use:** The staging or classification system combines categories across dimensions using if/then rules rather than point sums. The output is a stage or class, not a number.

**Examples:** R-ISS, TNM staging, Ann Arbor staging, FIGO staging, Rai/Binet staging (CLL)

**FHIR pattern:** Use `variable` extensions for intermediate boolean/categorical states + nested `iif()` expressions to derive the final classification.

### Hybrids

Some calculators mix types. IPSS-M combines formula-based continuous variables with weight-like binary gene coefficients. When in doubt, use the dominant pattern and adapt. A calculator with 2 numeric inputs and 15 weighted checkboxes is weight-based; a calculator with 15 continuous variables and 2 categorical ones is formula-based.

---

## Type 1: Weight-based pattern

This is the standard pattern for scored questionnaires in FHIR. Each answer option carries an `itemWeight` extension, and the score is computed using the `weight()` FHIRPath function.

### Structure

```
Questionnaire
├── [variable: totalScore = %resource.item.where(linkId='input-group').item.answer.value.weight().sum()]
├── input-group (group)
│   ├── question-1 (coding, with itemWeight on each answerOption)
│   ├── question-2 (coding, with itemWeight on each answerOption)
│   └── ...
└── result (group)
    ├── total-score (decimal, calculatedExpression: %totalScore)
    └── risk-category (string, calculatedExpression: iif(...))
```

### Key elements

**Item type:** Use `coding` (not `boolean`), even for yes/no questions. This is because `itemWeight` attaches to answer options, and boolean items don't have explicit answer options in FHIR.

**Answer options with weights:** Each `answerOption` gets an `itemWeight` extension with a `valueDecimal`:

```json
{
  "answerOption": [
    {
      "valueCoding": { "system": "http://snomed.info/sct", "code": "373067005", "display": "No" },
      "extension": [{
        "url": "http://hl7.org/fhir/StructureDefinition/itemWeight",
        "valueDecimal": 0
      }]
    },
    {
      "valueCoding": { "system": "http://snomed.info/sct", "code": "373066001", "display": "Yes" },
      "extension": [{
        "url": "http://hl7.org/fhir/StructureDefinition/itemWeight",
        "valueDecimal": 2
      }]
    }
  ]
}
```

**Score aggregation:** Define a `variable` at the **questionnaire level** (not on the input group) so that both the input group and the result group can reference it:

```json
{
  "url": "http://hl7.org/fhir/StructureDefinition/variable",
  "valueExpression": {
    "name": "totalScore",
    "language": "text/fhirpath",
    "expression": "%resource.item.where(linkId='input-group').item.answer.value.weight().sum()"
  }
}
```

The `weight()` function resolves the `itemWeight` from the selected answer option. The expression targets the input group's children explicitly via `%resource.item.where(linkId='input-group').item`, so all scored questions within that group are summed automatically without needing a separate variable per question.

Why questionnaire level? Variables scoped to a group are only visible to that group and its descendants — not to sibling groups. Since the result group is a sibling of the input group, a variable defined on the input group would not be accessible from result items. Defining at questionnaire level avoids this scoping trap.

**Risk category:** Use a `calculatedExpression` with nested `iif()`:

```
iif(%totalScore <= 0, 'Low', iif(%totalScore <= 2, 'Intermediate-1', iif(%totalScore <= 4, 'Intermediate-2', 'High')))
```

### Multi-weight groups

Some calculators (like HCT-CI) group comorbidities by weight — all 1-point items together, all 2-point items together, all 3-point items together. You can either:

- Put all items in one group and let `itemWeight` handle different weights per item (preferred)
- Use separate groups for clarity, with a questionnaire-level variable that sums across groups

### UI control

For yes/no weight-based questions, use the `chips` item control for a compact layout:

```json
{
  "url": "http://hl7.org/fhir/StructureDefinition/questionnaire-itemControl",
  "valueCodeableConcept": {
    "coding": [{ "system": "http://fhir.tiro.health/CodeSystem/tiro-questionnaire-item-control", "code": "chips" }]
  }
}
```

### References

- `itemWeight` extension: https://hl7.org/fhir/extensions/StructureDefinition-itemWeight.html
- `weight()` FHIRPath function: https://build.fhir.org/ig/HL7/sdc/en/expressions.html#fhirpath-supplements

---

## Type 2: Formula-based pattern

For calculators where numeric inputs feed into a mathematical formula. The key building blocks are `variable` extensions for intermediate computations and `calculatedExpression` for outputs.

### Structure

```
Questionnaire
├── [variable: inputA = %resource.item...answer.value]
├── [variable: inputB = %resource.item...answer.value]
├── [variable: transformed = %inputA * coefficient + %inputB / divisor]
├── inputs (group)
│   ├── field-a (decimal)
│   └── field-b (decimal)
└── result (group)
    ├── score (decimal, calculatedExpression: %transformed)
    └── category (string, calculatedExpression: iif(%transformed < cutoff, ...))
```

### Key elements

**Variables at questionnaire level:** For formula-based calculators, define variables at the questionnaire level (omit `--link-id` in CLI) so they're accessible everywhere. This avoids scoping issues where variables defined on one group aren't visible to sibling groups.

**Reading input values:** The FHIRPath pattern to read an answer from a nested item is:

```
%resource.item.where(linkId='group-id').item.where(linkId='item-id').answer.value
```

**Chained computations:** Break complex formulas into named intermediate variables rather than writing one enormous expression. This makes the logic readable and debuggable:

```
variable hbVal       = <read hemoglobin answer>
variable hbClinical  = %hbVal * -0.171
variable pltVal      = <read platelet answer>
variable pltClinical = iif(%pltVal > 250, 250, %pltVal) / 100 * -0.222
variable totalScore  = %hbClinical + %pltClinical + ...
```

**Input clamping:** Many formulas cap inputs at certain values (e.g. platelets capped at 250). Use `iif()` for this:

```
iif(%pltVal > 250, 250, %pltVal)
```

**FHIRPath limitations:** FHIRPath supports basic arithmetic (+, -, *, /), comparison operators, `iif()` for conditionals, and boolean logic (and, or, not). It does **not** support logarithms (`ln`, `log`), exponents (`pow`, `exp`), or complex math functions. Functions like `ln()` will fail at runtime even if they look syntactically reasonable.

When a formula requires these (e.g. MELD = 3.78×ln(Bilirubin) + 11.2×ln(INR) + 9.57×ln(Creatinine) + 6.43), you have two options:

1. **Lookup table approach** (preferred): Replace the continuous input with a `coding` item whose answer options represent clinically meaningful ranges, each mapped to the pre-computed transformed value via `itemWeight` or `iif()`. For example, bilirubin ranges (1-1.9, 2-2.9, 3-3.9, …) each carry the pre-computed `3.78×ln(midpoint)` as their weight. This gives clinically accurate results within each range.

2. **Linear approximation**: Fit a linear model to the nonlinear function over the clinically relevant input range. Document which range the approximation is valid for and what the maximum error is. Never invent coefficients — derive them from the actual formula using regression or Taylor expansion over the relevant domain.

### Coding items in formula calculators

When a formula includes a categorical variable mapped to numeric values (like IPSS-R cytogenetic risk: Very Good=0, Good=1, ..., Very Poor=4), use a `coding` item with answer options and map to the numeric value using `iif()`:

```
variable cytoCode = %resource.item...answer.value.code
variable cytoVec  = iif(%cytoCode = 'very-good', 0, iif(%cytoCode = 'good', 1, ...))
variable cytoPart = %cytoVec * 0.287
```

---

## Type 3: Discrete logic pattern

For staging systems and classifications where the output is a category derived from combining multiple categorical inputs through decision logic.

### Structure

```
Questionnaire
├── [variable: dimA = <read input A>]
├── [variable: dimB = <read input B>]
├── [variable: intermediateX = %dimA and %dimB.not()]
├── [variable: intermediateY = %dimA.not() and %dimB]
├── inputs (group)
│   ├── input-a (coding or boolean)
│   └── input-b (coding or boolean)
└── result (group)
    └── classification (string, calculatedExpression: iif(%intermediateX, 'Stage I', iif(%intermediateY, 'Stage II', 'Stage III')))
```

### Key elements

**Intermediate boolean variables:** Each "dimension" of the classification becomes a named variable. This makes the decision tree explicit and traceable — you can see exactly why a patient lands in a given category:

```
variable issStageI   = %b2mVal < 3.5 and %albVal >= 3.5
variable issStageIII = %b2mVal >= 5.5
variable highRiskCA  = %hasDel17p or %hasT414 or %hasT1416
variable normalLDH   = %ldhHigh.not()
```

**Final classification via nested iif():** Combine the intermediate variables into the output:

```
iif(%issStageI and %highRiskCA.not() and %normalLDH, 'R-ISS I',
  iif(%issStageIII and (%highRiskCA or %normalLDH.not()), 'R-ISS III',
    'R-ISS II'))
```

**"Everything else" category:** Many staging systems have a catch-all middle category (like R-ISS Stage II = "neither I nor III"). Put the most specific stages first in the `iif()` chain and let the catch-all be the final else.

**Boolean negation:** Use `.not()` in FHIRPath, not `!`:

```
%highRiskCA.not()    ← correct
!%highRiskCA         ← wrong
```

---

## General best practices

### Questionnaire structure

Always organize calculators into two main sections:

1. **Input section(s)** — one or more groups containing the questions
2. **Result section** — a group containing calculated output fields

This separation makes the form clear for clinicians: fill in the top, read the result at the bottom.

### Metadata

Include proper metadata for every calculator:

```bash
sdc meta --description "Full name of score. Based on Author et al. (Year), Journal." --status active
```

The description should credit the original publication. This is both good practice and helps clinicians trust the tool.

### Variable scoping

Variables defined on an item are available to that item and its descendants only. If you need a variable accessible across sibling groups (e.g. the input group and the result group both need it), define it at the questionnaire level by omitting `--link-id`.

Since calculators always have sibling input and result groups, **define all variables at the questionnaire level** unless you have a specific reason to scope them narrower. For weight-based calculators, this means using `%resource.item.where(linkId='input-group').item.answer.value.weight().sum()` to explicitly target the input group's children.

### Outcome data

Where available, include prognostic outcome data (median survival, 5-year OS, mortality rates) as additional calculated fields in the result section. Clinicians use these scores to guide treatment decisions, so showing the associated outcomes is more useful than just the raw score.

### Long pipelines

When building complex calculators with many items and variables, the `sdc` CLI pipe can break if it gets too long. Break the build into stages, saving intermediate JSON files:

```bash
sdc init ... | sdc item add ... | ... > /tmp/stage1.json
cat /tmp/stage1.json | sdc extension add variable ... | ... > /tmp/stage2.json
cat /tmp/stage2.json | sdc extension add calculated-expression ... | sdc validate > final.json
```

Redirect stderr separately from stdout (`2>/tmp/warnings.txt`) to avoid corrupting the JSON output.
