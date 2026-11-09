"""RFP-specific proposal content generation.

The legacy path in ``document_generator`` fills a fixed skeleton of 63SATS
boilerplate from the ~19 short fields produced by the extractors, so a firewall
RFP and a SOC RFP render nearly identical prose. This service closes that gap:
it sends the *full RFP text* to Claude once and asks for the narrative sections
written specifically for that RFP — the client's own requirements, the actual
products named in the tender, a real risk register — which the generators then
render in place of the hardcoded defaults.

Output is a flat ``{section_key: markdown_text}`` dict. Every value is plain
text using the conventions ``_add_body_text`` already understands: ``•``/``-``
bullets, ``1.`` numbered items, and ``|`` pipe tables.
"""

from __future__ import annotations

import json
from typing import Dict, Optional

import anthropic

from app.core.config import settings

# The key must be passed explicitly: pydantic-settings loads .env into
# `settings`, not into os.environ, so a bare Anthropic() finds no credential.
client = (
    anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    if settings.ANTHROPIC_API_KEY
    else None
)

MODEL = "claude-opus-5"

# Claude writes long-form prose for ~20 sections in one call, so the request
# needs real headroom and must stream to stay under the SDK HTTP timeout.
MAX_TOKENS = 32000

# The RFP is sent verbatim; truncate only to stay well inside the context window
# for pathological uploads (scanned tenders with hundreds of pages of annexures).
MAX_RFP_CHARS = 400_000


# Section key -> what the model should put there. Keys match the names the
# document generators look up in ``extracted_data``, so a generated section
# transparently replaces the corresponding hardcoded default.
SECTIONS: Dict[str, str] = {
    "executive_summary": (
        "3-5 paragraphs. Open by naming the client and the specific engagement "
        "they have tendered for. State what they asked for, why it matters to "
        "their business, what 63SATS proposes, and the headline outcome. Must "
        "read as though it could only have been written for this RFP - "
        "reference their sites, their industry, their drivers, their deadlines."
    ),
    "understanding_of_requirements": (
        "The single most important section. Demonstrate that 63SATS has read "
        "and understood THIS RFP. Restate the client's requirements in your own "
        "words, grouped under sub-headings, citing their specifics: named "
        "products and models, quantities, site/branch counts, throughput, user "
        "counts, existing infrastructure, integration points, compliance "
        "obligations, commercial and timeline constraints. Where the RFP is "
        "silent on something material, say so explicitly and state the "
        "assumption 63SATS has made. Never generic."
    ),
    "requirements_traceability": (
        "A markdown pipe table with exactly the columns: "
        "| RFP Requirement | 63SATS Response | Compliance |. "
        "One row per discrete requirement lifted from the RFP (aim for 12-25 "
        "rows). 'RFP Requirement' quotes or closely paraphrases the tender. "
        "'63SATS Response' says concretely how it is met. 'Compliance' is one "
        "of: Compliant, Compliant with Deviation, or Noted. Table only, no "
        "surrounding prose."
    ),
    "current_environment": (
        "Describe the client's existing environment as evidenced by the RFP: "
        "sites, links, existing security and network estate, what is being "
        "replaced or extended, and the gaps or pain points driving this "
        "procurement. If the RFP gives little detail, state what is known and "
        "flag what must be confirmed during discovery."
    ),
    "objectives": (
        "6-10 numbered objectives derived from the RFP's own stated goals, "
        "written in the client's terms rather than generic security outcomes."
    ),
    "technical_solution": (
        "The core engineering section, and the one that most often reads as "
        "generic - do not let it. Write the actual technical design for what "
        "this RFP asks for. If it is a firewall deployment, that means: the "
        "proposed platform and models with a sizing rationale, physical and "
        "logical architecture, interface and VLAN/zone design, high "
        "availability (HA pair mode, failover, heartbeat/sync links), routing, "
        "NAT, site-to-site and remote-access VPN design (topology, crypto "
        "suites, authentication), the security policy and inspection profile "
        "set (IPS, AV, web/app control, SSL inspection), centralised "
        "management and logging, and integration with the client's existing "
        "identity/SIEM/monitoring. If it is a SOC, OT, endpoint or audit "
        "engagement, write the equivalent depth for that domain instead. Use "
        "sub-headings and, where it helps, pipe tables. Name only technologies "
        "the RFP names or that are a defensible fit; never invent a client "
        "commitment to a product they did not mention."
    ),
    "bill_of_materials": (
        "A markdown pipe table with the columns: "
        "| Item | Description | Qty | Remarks |. "
        "List the hardware, software, licences, subscriptions and support "
        "entitlements the proposed solution requires, based on the RFP's stated "
        "quantities and sites. Put commercial figures in Remarks only if the "
        "RFP states them; otherwise write 'As per commercial annexure'. If the "
        "RFP does not describe a product-based solution, return an empty string."
    ),
    "assessment": (
        "Bulleted scope for the assessment and design phase, specific to this "
        "engagement's environment and deliverables."
    ),
    "implementation": (
        "Bulleted scope for the implementation and deployment phase, naming the "
        "actual activities this engagement requires (staging, configuration "
        "build, cutover windows, migration of existing rules/policies, "
        "testing, rollback)."
    ),
    "key_services": (
        "Bulleted list of the discrete services and deliverables 63SATS will "
        "hand over, drawn from the RFP's scope of work and deliverables "
        "clauses."
    ),
    "implementation_approach": (
        "The phased delivery approach for this engagement. Give each phase a "
        "name, the activities it contains, its exit criteria, and its "
        "deliverables. Phases must reflect this project's real shape, not a "
        "generic four-phase template."
    ),
    "implementation_methodology": (
        "Delivery methodology, governance cadence, change control, quality "
        "gates and acceptance criteria for this engagement."
    ),
    "timeline": (
        "A markdown pipe table with the columns: "
        "| Phase | Activities | Duration | Deliverable |, followed by one line "
        "giving the total duration. Honour any deadline or go-live date the RFP "
        "states."
    ),
    "raci_matrix": (
        "A markdown pipe table with exactly the columns: "
        "| Activity | 63SATS | Client | OEM/Partner |. Cells contain R, A, C or "
        "I. Rows must be the actual activities of THIS engagement (10-18 rows), "
        "not a generic MSSP activity list. Table only, no surrounding prose."
    ),
    "assumptions": (
        "Assumptions this proposal rests on, grouped under sub-headings, "
        "tied to the specifics of this RFP (site access, existing licences, "
        "downtime windows, information the tender did not provide)."
    ),
    "dependencies": (
        "What 63SATS needs from the client and from third parties to deliver, "
        "and the impact if each is not met. Specific to this engagement."
    ),
    "risk_mitigations": (
        "A substantial risk management section - this is frequently the "
        "weakest part of the proposal, so give it real depth. Open with one "
        "short paragraph on the risk management approach, then a markdown pipe "
        "table with exactly the columns: "
        "| # | Risk | Category | Impact | Likelihood | Mitigation | Owner |. "
        "Include 10-15 rows of risks genuinely specific to THIS engagement "
        "(technical, delivery, operational, commercial and security risks that "
        "arise from what this RFP actually asks for - for a firewall cutover "
        "that means things like traffic outage during migration, policy "
        "translation errors from the legacy ruleset, HA failover not behaving "
        "under load, VPN tunnel renegotiation with third parties, licence "
        "delivery lead time). Impact and Likelihood are High/Medium/Low. After "
        "the table, add short sub-sections on risk monitoring and review "
        "cadence, and on business continuity during the engagement."
    ),
    "expected_outcomes": (
        "The measurable outcomes this client gets, grouped and quantified. Tie "
        "each outcome back to an objective or requirement from the RFP."
    ),
    "why_63sats": (
        "Why 63SATS is the right partner FOR THIS ENGAGEMENT specifically. "
        "Connect capabilities, certifications and comparable delivery "
        "experience to the actual technology and domain this RFP covers. Do not "
        "write a generic company profile."
    ),
    "conclusion": (
        "2-3 closing paragraphs naming the client and the specific engagement, "
        "restating the value proposition in their terms."
    ),
}


SYSTEM_PROMPT = """You are a senior bid manager and solution architect at 63SATS \
Cybertech Limited, an Indian cybersecurity MSSP. You write the technical and \
narrative content of formal proposals submitted in response to client RFPs.

Your proposals are scored by evaluation committees against criteria such as \
Understanding of Client Requirements, Technical Solution, Scope of Work, \
Implementation Methodology, Project Management, Risk Management and Value \
Proposition. Committees mark down proposals that read as generic cybersecurity \
boilerplate. Every section you write must be visibly grounded in the specific \
RFP you are given: the client's name, their sites and quantities, the products \
and standards they named, their timelines, and their stated evaluation criteria.

Rules:
- Ground every claim in the RFP. Where the RFP is silent on something you need, \
state the assumption explicitly rather than inventing a fact about the client.
- Be concrete and technical. Prefer specific designs, numbers and named \
technologies over adjectives.
- Never fabricate 63SATS credentials, client references, prices, or commercial \
terms that were not supplied to you.
- Write in British/Indian business English, third person ("63SATS will..."), \
addressing the client by name or as "the Client".

Formatting: plain text only. No markdown headings (#), no bold (**), no code \
fences. You may use:
- Sub-headings as a short line of text on its own, immediately followed by its \
content.
- Bullets starting with "• " and numbered items starting with "1. ".
- Tables as markdown pipe tables with a header row and a |---|---| separator."""


def _schema() -> dict:
    return {
        "type": "object",
        "properties": {k: {"type": "string"} for k in SECTIONS},
        "required": list(SECTIONS),
        "additionalProperties": False,
    }


def _build_user_prompt(
    rfp_content: str,
    extracted_data: Dict,
    client_name: str,
    proposal_type: Optional[str],
) -> str:
    known = {
        k: v
        for k, v in (extracted_data or {}).items()
        if isinstance(v, str) and v.strip()
    }
    known_block = (
        json.dumps(known, indent=2, ensure_ascii=False)
        if known
        else "(no reviewed fields yet - work from the RFP text alone)"
    )

    spec = "\n\n".join(f'"{key}":\n{guidance}' for key, guidance in SECTIONS.items())

    rfp = (rfp_content or "").strip()
    if len(rfp) > MAX_RFP_CHARS:
        rfp = rfp[:MAX_RFP_CHARS] + "\n\n[RFP truncated for length]"

    return f"""Write the proposal content for the following RFP.

Client: {client_name}
Engagement type (auto-detected, may be approximate): {proposal_type or "not detected"}

Fields already extracted and reviewed by the bid team. These are authoritative \
where they conflict with your own reading of the RFP:
{known_block}

=== BEGIN RFP DOCUMENT ===
{rfp}
=== END RFP DOCUMENT ===

Produce one entry for each of the following keys. The guidance under each key \
describes what that section must contain.

{spec}

Return a JSON object with exactly these keys and string values."""


def write_proposal_sections(
    rfp_content: str,
    extracted_data: Dict,
    client_name: str,
    proposal_type: Optional[str] = None,
) -> Dict[str, str]:
    """Generate RFP-specific content for every narrative proposal section.

    Returns ``{section_key: text}``, or ``{}`` if generation is unavailable or
    fails — callers then fall back to the existing hardcoded defaults, matching
    how the extractors degrade.
    """
    if client is None:
        print(
            "[proposal_writer] SKIPPED: ANTHROPIC_API_KEY is not set. The proposal "
            "will render generic 63SATS boilerplate instead of RFP-specific content."
        )
        return {}
    if not rfp_content or not rfp_content.strip():
        print(
            "[proposal_writer] SKIPPED: the linked RFP has no extracted text. "
            "Re-upload the RFP (scanned PDFs often yield no text)."
        )
        return {}

    try:
        with client.messages.stream(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            output_config={
                "effort": "high",
                "format": {"type": "json_schema", "schema": _schema()},
            },
            messages=[
                {
                    "role": "user",
                    "content": _build_user_prompt(
                        rfp_content, extracted_data, client_name, proposal_type
                    ),
                }
            ],
        ) as stream:
            message = stream.get_final_message()
    except anthropic.AuthenticationError as e:
        print(
            f"[proposal_writer] FAILED: ANTHROPIC_API_KEY was rejected ({e}). "
            "Falling back to generic boilerplate — the proposal will NOT be "
            "specific to this RFP until a valid key is configured."
        )
        return {}
    except Exception as e:  # noqa: BLE001 - degrade to boilerplate, as extractors do
        print(f"[proposal_writer] FAILED: {type(e).__name__}: {e}")
        return {}

    if message.stop_reason == "refusal":
        print("Proposal writer: request was declined by safety classifiers")
        return {}

    text = next((b.text for b in message.content if b.type == "text"), "")
    try:
        sections = json.loads(text)
    except json.JSONDecodeError as e:
        print(f"Proposal writer: could not parse response as JSON: {e}")
        return {}

    if not isinstance(sections, dict):
        return {}

    return {
        k: v.strip()
        for k, v in sections.items()
        if k in SECTIONS and isinstance(v, str) and v.strip()
    }
