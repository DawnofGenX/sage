# Extraction Accuracy Evaluation

## What This Measures

This evaluation measures the **deterministic mock extractor** (regex-based fallback)
used when no LLM API key is configured. It does **NOT** measure the accuracy of a
frontier LLM extraction. The numbers reflect the extraction shape of the fallback
path — useful for understanding baseline behavior and anti-hallucination properties,
but should not be read as evidence that Sage extracts accurately in production.

## Per-Case Results

| Case | Field | TP | FP | FN | Precision | Recall |
|------|-------|----|----|----|-----------|--------|
| eval-01 | people | 1 | 1 | 1 | 0.50 | 0.50 |
| eval-01 | companies | 1 | 0 | 1 | 1.00 | 0.50 |
| eval-01 | amounts | 1 | 0 | 0 | 1.00 | 1.00 |
| eval-01 | dates | 1 | 0 | 1 | 1.00 | 0.50 |
| eval-02 | people | 1 | 0 | 1 | 1.00 | 0.50 |
| eval-02 | companies | 1 | 0 | 1 | 1.00 | 0.50 |
| eval-02 | amounts | 0 | 0 | 0 | — | — |
| eval-02 | dates | 1 | 0 | 2 | 1.00 | 0.33 |
| eval-03 | people | 1 | 1 | 1 | 0.50 | 0.50 |
| eval-03 | companies | 1 | 0 | 1 | 1.00 | 0.50 |
| eval-03 | amounts | 3 | 0 | 0 | 1.00 | 1.00 |
| eval-03 | dates | 0 | 0 | 1 | — | 0.00 |
| eval-04 | people | 1 | 1 | 1 | 0.50 | 0.50 |
| eval-04 | companies | 1 | 0 | 3 | 1.00 | 0.25 |
| eval-04 | amounts | 0 | 0 | 0 | — | — |
| eval-04 | dates | 0 | 0 | 0 | — | — |
| eval-05 | people | 1 | 1 | 1 | 0.50 | 0.50 |
| eval-05 | companies | 0 | 0 | 2 | — | 0.00 |
| eval-05 | amounts | 2 | 0 | 0 | 1.00 | 1.00 |
| eval-05 | dates | 0 | 0 | 1 | — | 0.00 |
| eval-06 | people | 3 | 0 | 1 | 1.00 | 0.75 |
| eval-06 | companies | 0 | 0 | 2 | — | 0.00 |
| eval-06 | amounts | 1 | 0 | 0 | 1.00 | 1.00 |
| eval-06 | dates | 0 | 0 | 0 | — | — |
| eval-07 | people | 0 | 0 | 0 | — | — |
| eval-07 | companies | 0 | 0 | 0 | — | — |
| eval-07 | amounts | 0 | 0 | 0 | — | — |
| eval-07 | dates | 0 | 0 | 0 | — | — |
| eval-08 | people | 0 | 1 | 0 | 0.00 | — |
| eval-08 | companies | 0 | 0 | 2 | — | 0.00 |
| eval-08 | amounts | 0 | 0 | 0 | — | — |
| eval-08 | dates | 0 | 0 | 2 | — | 0.00 |
| eval-09 | people | 1 | 1 | 1 | 0.50 | 0.50 |
| eval-09 | companies | 1 | 0 | 1 | 1.00 | 0.50 |
| eval-09 | amounts | 1 | 0 | 1 | 1.00 | 0.50 |
| eval-09 | dates | 0 | 0 | 0 | — | — |
| eval-10 | people | 0 | 0 | 0 | — | — |
| eval-10 | companies | 0 | 0 | 0 | — | — |
| eval-10 | amounts | 0 | 0 | 0 | — | — |
| eval-10 | dates | 0 | 0 | 0 | — | — |

## Per-Field Aggregates

| Field | Total TP | Total FP | Total FN | Precision | Recall |
|-------|----------|----------|----------|-----------|--------|
| people | 9 | 6 | 7 | 0.60 | 0.56 |
| companies | 5 | 0 | 13 | 1.00 | 0.28 |
| amounts | 8 | 0 | 1 | 1.00 | 0.89 |
| dates | 2 | 0 | 7 | 1.00 | 0.22 |

## Anti-Hallucination Analysis

Cases eval-07, eval-08, and eval-10 have empty `people` labels (and in some cases
other fields too). For these cases, recall is **None** (no labels to find), but
precision is meaningful: returning any person is a false positive.

- **eval-07**: people precision = —
- **eval-08**: people precision = 0.00
- **eval-10**: people precision = —

## What This Does NOT Measure

- **LLM accuracy**: The mock extractor uses regex, not a language model. These numbers
  say nothing about how well GPT-4o or Claude would extract entities.
- **Production behavior**: In production with an API key, the pipeline uses real LLM
  calls. The mock path is a fallback for demo/testing only.
- **Intent, sentiment, or record extraction**: Only entity extraction (pass 1) is measured.
- **Generalization**: 10 hand-labelled cases is a small sample. Results may not generalize
  to other transcript styles or domains.
