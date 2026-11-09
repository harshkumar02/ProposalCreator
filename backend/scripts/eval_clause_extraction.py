"""Score clause extraction against the sample tender's known answers.

Makes real (paid) model calls. Usage, from backend/:
    python -m scripts.eval_clause_extraction --provider gemini --model gemini-3.8-flash
    python -m scripts.eval_clause_extraction --provider claude
"""
import argparse
import sys
import time
from pathlib import Path

from app.core.config import settings
from app.services.clause_extractor import extract_clauses

TENDER = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "sample_tender.txt"


def _find(clauses, category, *words, exclude=()):
    for c in clauses:
        text = f"{c['requirement']} {c.get('source_text') or ''}".lower()
        if c["category"] == category and all(w in text for w in words) and not any(x in text for x in exclude):
            return c
    return None


def score(out):
    cl, td = out.clauses, out.tender_details
    turnover = _find(cl, "PQ", "turnover")
    experience = _find(cl, "PQ", "50 lakh") or _find(cl, "PQ", "vapt", "assignment")
    soc = _find(cl, "PQ", "eps")
    certin = _find(cl, "PQ", "cert-in", exclude=("report", "6 hours"))
    soc2_mandatory = [c for c in cl if "soc 2" in c["requirement"].lower() and c["mandatory"] is True]
    tq = [c for c in cl if c["category"] == "TQ"]
    tq_marks = {c["section_ref"]: c["max_marks"] for c in tq if c.get("section_ref")}
    pq = [c for c in cl if c["category"] == "PQ"]

    checks = {
        "turnover = Rs 20 Cr (corrigendum applied)": bool(turnover) and turnover["threshold_value"] == 200_000_000,
        "turnover flagged amended_by corrigendum": bool(turnover) and bool(turnover.get("amended_by")),
        "turnover on page 3, mandatory": bool(turnover) and turnover["page_number"] == 3 and turnover["mandatory"] is True,
        "experience: 2 projects (corrigendum) of Rs 50 lakh": bool(experience) and experience["min_count"] == 2 and experience["threshold_value"] == 5_000_000,
        "SOC contracts: min 2": bool(soc) and soc["min_count"] == 2,
        "CERT-In empanelment mandatory": bool(certin) and certin["mandatory"] is True,
        "net worth clause present": _find(cl, "PQ", "net worth") is not None,
        "blacklisting clause present": _find(cl, "PQ", "blacklist") is not None,
        "SOC 2 Type II NOT mandatory": not soc2_mandatory,
        ">= 9 mandatory PQ (injection ignored)": sum(1 for c in pq if c["mandatory"] is True) >= 9,
        "every PQ has a page": all(c["page_number"] for c in pq),
        "TQ A1 = 10, B1 = 4, D = 25 marks": tq_marks.get("A1") == 10 and tq_marks.get("B1") == 4 and tq_marks.get("D") == 25,
        "TQ marks sum to 100": abs(sum(c["max_marks"] or 0 for c in tq) - 100) < 0.01,
        "PBG 5% clause present": _find(cl, "COMMERCIAL", "5%") is not None or _find(cl, "COMMERCIAL", "performance bank guarantee") is not None,
        "tender id": td.get("tender_id") == "SVUCB/IT/2026/014",
        "deadline = 22 Dec (corrigendum)": "22" in str(td.get("submission_deadline") or "") and "dec" in str(td.get("submission_deadline") or "").lower(),
        "EMD = Rs 10 lakh": td.get("emd_amount_inr") == 1_000_000,
        "estimated value = Rs 18 Cr": td.get("estimated_value_inr") == 180_000_000,
        "TQ cut-off = 70": td.get("tq_cutoff_marks") == 70,
        "consortium not allowed": td.get("consortium_allowed") is False,
    }
    return checks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", default=settings.LLM_PROVIDER)
    parser.add_argument("--model", help="overrides GEMINI_MODEL / CLAUDE_MODEL for this run")
    args = parser.parse_args()
    if args.model:
        setattr(settings, "GEMINI_MODEL" if args.provider == "gemini" else "CLAUDE_MODEL", args.model)
    model = settings.GEMINI_MODEL if args.provider == "gemini" else settings.CLAUDE_MODEL

    start = time.time()
    out = extract_clauses(TENDER.read_text(encoding="utf-8"), provider=args.provider)
    elapsed = time.time() - start

    checks = score(out)
    passed = sum(checks.values())
    print(f"{args.provider}/{model}: {passed}/{len(checks)} checks, {elapsed:.0f}s, "
          f"{len(out.clauses)} clauses, {out.chunks} chunk(s), {out.amendments_applied} corrigendum update(s)")
    for name, ok in checks.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    by_cat = {}
    for c in out.clauses:
        by_cat[c["category"]] = by_cat.get(c["category"], 0) + 1
    print("  categories:", by_cat)
    if not checks["TQ marks sum to 100"]:
        for c in out.clauses:
            if c["category"] == "TQ":
                print(f"  TQ {c['section_ref'] or '-':>5} {c['max_marks']!s:>5}  {c['requirement'][:90]}")
    for w in out.warnings[:8]:
        print("  warning:", w[:160])
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
