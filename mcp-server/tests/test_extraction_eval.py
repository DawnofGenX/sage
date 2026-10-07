"""Measure extraction pipeline accuracy against a hand-labelled fixture.

This module measures the DETERMINISTIC MOCK extractor (regex-based fallback),
not a frontier LLM. The measurement is hermetic and deterministic. The numbers
reflect the extraction SHAPE of the fallback path, not model quality.
"""
import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

from extraction.pipeline import ExtractionPipeline
from llm.provider import LLMProvider

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "eval_transcripts.json"
REPORT_PATH = Path(__file__).parent.parent / "docs" / "extraction-eval.md"

FIELDS = ["people", "companies", "amounts", "dates"]
ANTI_HALLUCINATION_CASES = {"eval-07", "eval-08", "eval-10"}


def _normalize(s: str) -> str:
    """Normalize for case-insensitive comparison."""
    return s.lower().strip()


def _matches(prediction: str, label: str) -> bool:
    """Check if prediction matches label via normalized substring matching."""
    pred_norm = _normalize(prediction)
    label_norm = _normalize(label)
    return pred_norm in label_norm or label_norm in pred_norm


def _compute_field_metrics(predictions: list[str], labels: list[str]) -> dict[str, Any]:
    """Compute TP, FP, FN, precision, recall for one field."""
    tp = 0
    fp = 0
    matched_label_indices: set[int] = set()

    for pred in predictions:
        found = False
        for i, label in enumerate(labels):
            if _matches(pred, label):
                tp += 1
                found = True
                matched_label_indices.add(i)
                break
        if not found:
            fp += 1

    fn = len(labels) - len(matched_label_indices)
    precision = tp / (tp + fp) if (tp + fp) > 0 else None
    recall = tp / (tp + fn) if (tp + fn) > 0 else None

    return {"tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall}


def _run_pipeline(transcript: str) -> dict[str, list[str]]:
    """Run the extraction pipeline in mock mode on a transcript."""
    provider = LLMProvider(api_key="", api_url="http://localhost:9999", model="test-model")
    pipeline = ExtractionPipeline(provider)
    result = asyncio.run(pipeline.process(transcript))
    return result["step1_entities"]


def _fmt(v: Any) -> str:
    """Format a metric value for display."""
    if v is None:
        return "—"
    return f"{v:.2f}"


def _generate_report(results: list[dict[str, Any]]) -> str:
    """Generate the markdown evaluation report."""
    lines: list[str] = []
    lines.append("# Extraction Accuracy Evaluation")
    lines.append("")
    lines.append("## What This Measures")
    lines.append("")
    lines.append(
        "This evaluation measures the **deterministic mock extractor** (regex-based fallback)"
    )
    lines.append("used when no LLM API key is configured. It does **NOT** measure the accuracy of a")
    lines.append("frontier LLM extraction. The numbers reflect the extraction shape of the fallback")
    lines.append(
        "path — useful for understanding baseline behavior and anti-hallucination properties,"
    )
    lines.append("but should not be read as evidence that Sage extracts accurately in production.")
    lines.append("")
    lines.append("## Per-Case Results")
    lines.append("")
    lines.append("| Case | Field | TP | FP | FN | Precision | Recall |")
    lines.append("|------|-------|----|----|----|-----------|--------|")

    for case_result in results:
        case_id = case_result["id"]
        for field in FIELDS:
            m = case_result["fields"][field]
            lines.append(
                f"| {case_id} | {field} | {m['tp']} | {m['fp']} | {m['fn']} "
                f"| {_fmt(m['precision'])} | {_fmt(m['recall'])} |"
            )

    lines.append("")
    lines.append("## Per-Field Aggregates")
    lines.append("")
    lines.append("| Field | Total TP | Total FP | Total FN | Precision | Recall |")
    lines.append("|-------|----------|----------|----------|-----------|--------|")

    for field in FIELDS:
        total_tp = sum(r["fields"][field]["tp"] for r in results)
        total_fp = sum(r["fields"][field]["fp"] for r in results)
        total_fn = sum(r["fields"][field]["fn"] for r in results)
        agg_p = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else None
        agg_r = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else None
        lines.append(
            f"| {field} | {total_tp} | {total_fp} | {total_fn} "
            f"| {_fmt(agg_p)} | {_fmt(agg_r)} |"
        )

    lines.append("")
    lines.append("## Anti-Hallucination Analysis")
    lines.append("")
    lines.append(
        "Cases eval-07, eval-08, and eval-10 have empty `people` labels (and in some cases"
    )
    lines.append("other fields too). For these cases, recall is **None** (no labels to find), but")
    lines.append("precision is meaningful: returning any person is a false positive.")
    lines.append("")

    for case_result in results:
        if case_result["id"] in ANTI_HALLUCINATION_CASES:
            people_m = case_result["fields"]["people"]
            lines.append(f"- **{case_result['id']}**: people precision = {_fmt(people_m['precision'])}")

    lines.append("")
    lines.append("## What This Does NOT Measure")
    lines.append("")
    lines.append(
        "- **LLM accuracy**: The mock extractor uses regex, not a language model. These numbers"
    )
    lines.append("  say nothing about how well GPT-4o or Claude would extract entities.")
    lines.append(
        "- **Production behavior**: In production with an API key, the pipeline uses real LLM"
    )
    lines.append("  calls. The mock path is a fallback for demo/testing only.")
    lines.append(
        "- **Intent, sentiment, or record extraction**: Only entity extraction (pass 1) is measured."
    )
    lines.append(
        "- **Generalization**: 10 hand-labelled cases is a small sample. Results may not generalize"
    )
    lines.append("  to other transcript styles or domains.")
    lines.append("")

    return "\n".join(lines)


def _load_fixture() -> list[dict[str, Any]]:
    return json.loads(FIXTURE_PATH.read_text())


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------


def test_fixture_has_10_cases():
    """Assert the fixture has exactly 10 cases."""
    data = _load_fixture()
    assert len(data) == 10, f"Expected 10 cases, got {len(data)}"


def test_every_case_has_id_and_expected():
    """Assert every case has an id and expected field."""
    data = _load_fixture()
    for case in data:
        assert "id" in case, f"Case missing 'id': {case}"
        assert "expected" in case, f"Case {case.get('id')} missing 'expected'"


def test_metrics_computation():
    """Unit test for the metrics computation logic."""
    # Perfect match
    m = _compute_field_metrics(["Alice", "Bob"], ["Alice", "Bob"])
    assert m["tp"] == 2
    assert m["fp"] == 0
    assert m["fn"] == 0
    assert m["precision"] == 1.0
    assert m["recall"] == 1.0

    # Partial match
    m = _compute_field_metrics(["Alice", "Charlie"], ["Alice", "Bob"])
    assert m["tp"] == 1
    assert m["fp"] == 1
    assert m["fn"] == 1
    assert m["precision"] == 0.5
    assert m["recall"] == 0.5

    # No predictions, some labels
    m = _compute_field_metrics([], ["Alice"])
    assert m["tp"] == 0
    assert m["fp"] == 0
    assert m["fn"] == 1
    assert m["precision"] is None
    assert m["recall"] == 0.0

    # Some predictions, no labels
    m = _compute_field_metrics(["Alice"], [])
    assert m["tp"] == 0
    assert m["fp"] == 1
    assert m["fn"] == 0
    assert m["precision"] == 0.0
    assert m["recall"] is None

    # Neither predictions nor labels
    m = _compute_field_metrics([], [])
    assert m["precision"] is None
    assert m["recall"] is None


def test_extraction_eval_writes_report():
    """Run the full evaluation and write the report."""
    data = _load_fixture()
    results = []

    for case in data:
        entities = _run_pipeline(case["transcript"])
        case_results = {}
        for field in FIELDS:
            predictions = entities.get(field, [])
            labels = case["expected"].get(field, [])
            case_results[field] = _compute_field_metrics(predictions, labels)
        results.append({"id": case["id"], "fields": case_results})

    report = _generate_report(results)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report)

    assert REPORT_PATH.exists(), f"Report not written to {REPORT_PATH}"
    assert len(report) > 0, "Report is empty"
    assert "Anti-Hallucination" in report
    assert "What This Does NOT Measure" in report
