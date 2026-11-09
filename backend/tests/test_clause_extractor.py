import pytest

from app.services import clause_extractor as ce
from app.services.llm import LLMError


def _clause(**overrides):
    base = {
        "category": "PQ", "criterion_type": "turnover", "requirement": "Average annual turnover >= INR 25 crore",
        "source_text": "The bidder shall have average annual turnover of Rs 25 crore.", "mandatory": True,
        "threshold_value": 250000000, "threshold_unit": "INR", "operator": ">=", "period": "last 3 FYs",
        "min_count": None, "max_marks": None, "scoring_rule": None, "evidence_required": ["CA certificate"],
        "page": 2, "section_ref": "3.1(a)", "confidence": 0.9,
    }
    base.update(overrides)
    return base


def _result(clauses=(), amendments=(), warnings=(), **tender):
    details = {key: None for key in ce.TENDER_FIELDS}
    details.update(tender)
    return {"tender_details": details, "clauses": list(clauses), "amendments": list(amendments), "warnings": list(warnings)}


def test_split_pages_reads_markers_and_keeps_preamble():
    pages = ce.split_pages("Cover note\n--- Page 1 ---\nIntro\n--- Page 2 ---\nPQ criteria\n")
    assert pages == [(None, "Cover note"), (1, "Intro"), (2, "PQ criteria")]


def test_split_pages_without_markers_is_one_unnumbered_page():
    assert ce.split_pages("plain docx text") == [(None, "plain docx text")]


def test_chunk_pages_respects_limit_and_keeps_markers():
    pages = [(1, "a" * 60), (2, "b" * 60), (3, "c" * 60)]
    chunks = ce.chunk_pages(pages, limit=160)  # each block is 15-char marker + 60
    assert [numbers for numbers, _ in chunks] == [[1, 2], [3]]
    assert chunks[0][1].startswith("--- Page 1 ---") and "--- Page 2 ---" in chunks[0][1]


def test_chunk_pages_splits_an_oversized_page_and_repeats_its_marker():
    chunks = ce.chunk_pages([(7, "x" * 250)], limit=100)
    assert len(chunks) == 3
    assert all(numbers == [7] for numbers, _ in chunks)
    assert all(text.startswith("--- Page 7 ---") for _, text in chunks)


def test_normalise_rejects_bad_values_instead_of_trusting_the_model():
    warnings = []
    clause = ce.normalise_clause(
        _clause(category="eligibility", criterion_type="Net Worth", operator="at least", threshold_value="abc",
                mandatory="yes", min_count=-2, page=99, confidence=7),
        valid_pages=[1, 2], warnings=warnings,
    )
    assert clause["category"] == "ADMIN"
    assert clause["criterion_type"] == "net_worth"
    assert clause["operator"] is None
    assert clause["threshold_value"] is None
    assert clause["mandatory"] is None
    assert clause["min_count"] is None
    assert clause["page_number"] is None  # page 99 isn't in this chunk
    assert clause["confidence"] == 1.0
    assert any("category" in w for w in warnings) and any("Page 99" in w for w in warnings)


def test_normalise_drops_pages_for_documents_without_markers():
    clause = ce.normalise_clause(_clause(page=4), valid_pages=[None], warnings=[])
    assert clause["page_number"] is None


def test_normalise_skips_clauses_without_requirement():
    assert ce.normalise_clause(_clause(requirement="  "), [2], []) is None


def test_extract_clauses_merges_chunks_codes_and_tender_details(monkeypatch):
    content = "--- Page 1 ---\n" + "a" * 30 + "\n--- Page 2 ---\n" + "b" * 30
    monkeypatch.setattr(ce, "CHUNK_CHAR_LIMIT", 50)  # forces one page per chunk

    def fake(system, prompt, schema, provider=None, max_tokens=0):
        if "part 1 of 2" in prompt:
            return _result([_clause(category="TQ", requirement="SOC experience", max_marks=10, page=1, criterion_type=None)],
                           tender_id="TND/1", warnings=["Clause 4 is ambiguous"])
        return _result([_clause(page=2), _clause(page=2)], tender_id="ignored", emd_amount_inr=1000000)

    monkeypatch.setattr(ce, "complete_json", fake)
    progress = []
    out = ce.extract_clauses(content, provider="gemini", on_progress=progress.append)

    assert out.chunks == 2
    assert [c["clause_code"] for c in out.clauses] == ["PQ-001", "TQ-001"]  # duplicate PQ removed, PQ sorted first
    assert out.tender_details["tender_id"] == "TND/1" and out.tender_details["emd_amount_inr"] == 1000000
    assert out.warnings == ["Clause 4 is ambiguous"]
    assert progress[0] == "Extracting clauses: 0/2 parts" and progress[-1] == "Extracting clauses: 2/2 parts"


def test_extract_clauses_applies_corrigendum_from_another_chunk(monkeypatch):
    content = "--- Page 1 ---\n" + "a" * 30 + "\n--- Page 9 ---\n" + "b" * 30
    monkeypatch.setattr(ce, "CHUNK_CHAR_LIMIT", 50)
    amendment = {"target_section_ref": "3.1(a)", "target_summary": "turnover", "corrigendum_ref": "Corrigendum-1",
                 "amended_text": "Average turnover reduced to Rs 20 crore", "page": 9}
    calls = []

    def fake(system, prompt, schema, provider=None, max_tokens=0):
        calls.append(schema)
        if schema is ce.RECONCILE_SCHEMA:
            updates = {key: None for key in ce.TENDER_FIELDS}
            updates["submission_deadline"] = "22 December 2026 15:00 IST"
            return {"updates": [{"clause_index": 0, "amendment_index": 0,
                                 "clause": _clause(threshold_value=200000000, requirement="Average turnover >= INR 20 crore", page=None)}],
                    "unmatched_amendments": [], "tender_details_updates": updates}
        if "part 1 of 2" in prompt:
            return _result([_clause(page=1)], submission_deadline="15 December 2026 15:00 IST")
        return _result([], amendments=[amendment])

    monkeypatch.setattr(ce, "complete_json", fake)
    out = ce.extract_clauses(content)

    [clause] = out.clauses
    assert out.amendments_applied == 1
    assert clause["threshold_value"] == 200000000
    assert clause["amended_by"] == "Corrigendum-1"
    assert clause["page_number"] == 1  # keeps the original clause's location
    assert clause["original"]["threshold_value"] == 250000000
    assert calls.count(ce.RECONCILE_SCHEMA) == 1
    assert out.tender_details["submission_deadline"] == "22 December 2026 15:00 IST"
    assert out.tender_details["_before_corrigendum"] == {"submission_deadline": "15 December 2026 15:00 IST"}
    assert out.tender_details["_amended_fields"] == ["submission_deadline"]


def test_unmatched_corrigendum_becomes_a_warning(monkeypatch):
    amendment = {"target_section_ref": "9.9", "target_summary": "x", "corrigendum_ref": "Addendum-2",
                 "amended_text": "New clause about insurance", "page": 1}

    def fake(system, prompt, schema, provider=None, max_tokens=0):
        if schema is ce.RECONCILE_SCHEMA:
            return {"updates": [{"clause_index": 5, "amendment_index": 0, "clause": _clause()}], "unmatched_amendments": [0],
                    "tender_details_updates": {key: None for key in ce.TENDER_FIELDS}}
        return _result([_clause(page=1)], amendments=[amendment])

    monkeypatch.setattr(ce, "complete_json", fake)
    out = ce.extract_clauses("--- Page 1 ---\ntext")

    assert out.amendments_applied == 0
    assert any("invalid indexes" in w for w in out.warnings)
    assert any("Addendum-2" in w for w in out.warnings)


def test_chunk_failure_raises_with_part_number(monkeypatch):
    def fake(*args, **kwargs):
        raise LLMError("Gemini API error 429: quota")

    monkeypatch.setattr(ce, "complete_json", fake)
    with pytest.raises(LLMError, match=r"Part 1/1 failed: Gemini API error 429"):
        ce.extract_clauses("--- Page 1 ---\nsome tender text")


def test_empty_content_raises():
    with pytest.raises(LLMError, match="no text"):
        ce.extract_clauses("   ")
