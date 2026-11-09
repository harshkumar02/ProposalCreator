from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import hashlib
import json
import io

from app.core.database import get_db
from app.models.models import Proposal, ProposalType, RFP, Template, User, ExtractionResult
from app.api.auth import get_current_user
from app.services.document_generator import generate_proposal_document, apply_template_with_placeholders
from app.services.proposal_writer import write_proposal_sections

router = APIRouter()

# Key under which the AI-written, RFP-specific sections are cached inside
# Proposal.extracted_data, alongside a fingerprint of the inputs that produced
# them. Prefixed with "_" so it can never collide with an extraction field name.
AI_SECTIONS_KEY = "_ai_sections"
AI_FINGERPRINT_KEY = "_ai_fingerprint"


def _reviewed_fields(db: Session, proposal: Proposal, reviewed_only: bool = True) -> dict:
    """Extraction rows for the proposal's RFP, as {field_name: value}."""
    if not proposal.rfp_id:
        return {}
    q = db.query(ExtractionResult).filter(ExtractionResult.rfp_id == proposal.rfp_id)
    if reviewed_only:
        q = q.filter(ExtractionResult.is_reviewed == True)  # noqa: E712
    return {r.field_name: r.value for r in q.all() if r.value}


def _proposal_type_name(db: Session, proposal: Proposal):
    if not proposal.proposal_type_id:
        return None
    pt = db.query(ProposalType).filter(
        ProposalType.id == proposal.proposal_type_id
    ).first()
    return (pt.display_name or pt.name) if pt else None


def _build_generation_data(
    db: Session, proposal: Proposal, reviewed_only: bool = True
) -> dict:
    """Assemble the field dict the document generators render from.

    Three layers, lowest precedence first:

    1. AI-written sections generated from the full RFP text (this is what makes
       a proposal specific to the RFP rather than generic MSSP boilerplate).
    2. Whatever the user saved on ``Proposal.extracted_data``.
    3. Extraction rows the user has reviewed — explicit human edits always win.

    Anything still missing falls back to the hardcoded defaults inside
    ``document_generator``, so this degrades rather than fails.
    """
    stored = {}
    if proposal.extracted_data:
        try:
            stored = json.loads(proposal.extracted_data)
        except json.JSONDecodeError:
            stored = {"raw_data": proposal.extracted_data}
    if not isinstance(stored, dict):
        stored = {}

    manual = {k: v for k, v in stored.items() if not k.startswith("_")}
    reviewed = _reviewed_fields(db, proposal, reviewed_only=reviewed_only)

    ai_sections = _get_or_write_ai_sections(db, proposal, stored, {**manual, **reviewed})

    return {**ai_sections, **manual, **reviewed}


def _get_or_write_ai_sections(
    db: Session, proposal: Proposal, stored: dict, known_fields: dict
) -> dict:
    """Return the RFP-specific sections, generating them if not already cached.

    Generation is an expensive model call, so the result is cached on the
    proposal and only regenerated when the RFP text or the reviewed fields that
    feed the prompt actually change.
    """
    if not proposal.rfp_id:
        return {}

    rfp = db.query(RFP).filter(RFP.id == proposal.rfp_id).first()
    if not rfp or not rfp.content:
        return {}

    fingerprint = hashlib.sha256(
        json.dumps(
            {
                "rfp": rfp.content,
                "fields": known_fields,
                "client": proposal.client_name,
            },
            sort_keys=True,
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()

    cached = stored.get(AI_SECTIONS_KEY)
    if isinstance(cached, dict) and cached and stored.get(AI_FINGERPRINT_KEY) == fingerprint:
        return cached

    sections = write_proposal_sections(
        rfp_content=rfp.content,
        extracted_data=known_fields,
        client_name=proposal.client_name,
        proposal_type=_proposal_type_name(db, proposal),
    )
    if not sections:
        # Generation unavailable (no API key) or failed — keep any previous
        # sections rather than dropping back to boilerplate mid-flight.
        return cached if isinstance(cached, dict) else {}

    stored[AI_SECTIONS_KEY] = sections
    stored[AI_FINGERPRINT_KEY] = fingerprint
    proposal.extracted_data = json.dumps(stored, ensure_ascii=False)
    db.commit()

    return sections


# Fixed content
ABOUT_63SATS = """63SATS, driven by the innovative technology of 63 moons technologies ltd., stands as a comprehensive cybersecurity solutions provider catering to the needs of enterprises. Renowned as trailblazers in both digital markets and cybersecurity, we specialize in ensuring top-notch security for Enterprises, Industries & Government sectors.

63SATS brings you internationally recognized products and manages services with a mission to safeguard invaluable assets against the entire spectrum of sophisticated cyber threats. To position our clients as leading models of secure digital entities in India and globally, 63SATS Cybertech Limited as a security consulting & solution providing company has forged strategic partnerships with top-tier security product companies across the globe."""

WHY_63SATS = """63SATS is the right partner for this engagement because:

1. Expertise
   • Team of certified cybersecurity professionals (CISSP, CISM, CEH, OSCP)
   • Extensive experience with enterprise security implementations
   • Continuous training and knowledge development
   • Deep expertise across multiple security domains

2. Partnership & Technology
   • Relationships with leading technology vendors
   • Vendor-neutral approach to recommend best-fit solutions
   • Direct access to vendor engineering and support teams
   • Joint go-to-market capabilities

3. Customer Focus
   • Dedicated account management
   • Customized service delivery aligned to your needs
   • Flexible engagement models
   • Proven track record with similar organizations
   • Transparent communication and regular updates

4. Technology Leadership
   • Cloud-native platform expertise
   • Integration with existing tools and workflows
   • Continuous platform optimization
   • Access to emerging security capabilities

5. Value Proposition
   • Competitive and transparent pricing
   • No hidden fees or surprise charges
   • Predictable cost structure (OpEx vs CapEx)
   • Measurable outcomes and ROI
   • Commitment to customer success"""


@router.post("/{proposal_id}/generate")
def generate_proposal(
    proposal_id: int,
    template_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    proposal = db.query(Proposal).filter(
        Proposal.id == proposal_id,
        Proposal.user_id == current_user.id
    ).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    # Get template
    if template_id:
        template = db.query(Template).filter(
            Template.id == template_id,
            Template.user_id == current_user.id
        ).first()
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
    else:
        template = db.query(Template).filter(
            Template.user_id == current_user.id,
            Template.is_default == True
        ).first()

    extracted_data = _build_generation_data(db, proposal, reviewed_only=True)

    # Generate document using 63SATS format
    docx_content = generate_proposal_document(
        template_content=template.content if template else None,
        extracted_data=extracted_data
    )

    return StreamingResponse(
        io.BytesIO(docx_content),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f"attachment; filename=63SATS_Proposal_{proposal.client_name.replace(' ', '_')}.docx"
        }
    )


@router.post("/{proposal_id}/generate-text")
def generate_proposal_text(
    proposal_id: int,
    template_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate proposal as text (useful for preview) - 63SATS format."""
    proposal = db.query(Proposal).filter(
        Proposal.id == proposal_id,
        Proposal.user_id == current_user.id
    ).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    # Get template
    if template_id:
        template = db.query(Template).filter(
            Template.id == template_id,
            Template.user_id == current_user.id
        ).first()
    else:
        template = db.query(Template).filter(
            Template.user_id == current_user.id,
            Template.is_default == True
        ).first()

    extracted_data = _build_generation_data(db, proposal, reviewed_only=False)

    # Generate text from template
    if template and template.content:
        text = apply_template_with_placeholders(template.content, extracted_data)
    else:
        text = generate_63sats_proposal_text(extracted_data, proposal.client_name)

    return {"text": text}


def generate_63sats_proposal_text(data: dict, client_name: str) -> str:
    """Generate a 63SATS formatted proposal text."""
    lines = []

    # Title
    project_title = data.get('project_title', 'Cybersecurity Services Proposal')
    lines.append("=" * 80)
    lines.append("63SATS")
    lines.append(project_title)
    lines.append("=" * 80)
    lines.append("")
    lines.append(f"Submitted to: {client_name}")
    lines.append(f"Date: {data.get('date', '23rd May 2026')}")
    lines.append(f"Proposal No: {data.get('proposal_no', 'CR-XXXX-2026')}")
    lines.append("")

    # Executive Summary
    if data.get('executive_summary'):
        lines.append("EXECUTIVE SUMMARY")
        lines.append("-" * 80)
        lines.append("")
        lines.append(data['executive_summary'])
        lines.append("")

    # Section 1: Introduction
    lines.append("1. INTRODUCTION")
    lines.append("-" * 80)
    lines.append("")
    lines.append("1.1 About 63SATS")
    lines.append("")
    lines.append(ABOUT_63SATS)
    lines.append("")

    lines.append("1.2 Proposal Overview")
    lines.append("")
    overview = data.get('proposal_overview', f"This proposal is submitted by 63SATS for {project_title}.")
    lines.append(overview)
    lines.append("")

    # Understanding of Client Requirements
    if data.get('understanding_of_requirements'):
        lines.append("UNDERSTANDING OF CLIENT REQUIREMENTS")
        lines.append("-" * 80)
        lines.append("")
        lines.append(data['understanding_of_requirements'])
        lines.append("")
        if data.get('requirements_traceability'):
            lines.append("Requirement Compliance Matrix")
            lines.append("")
            lines.append(data['requirements_traceability'])
            lines.append("")

    # Section 2: Current Environment
    lines.append("2. CURRENT ENVIRONMENT SUMMARY")
    lines.append("-" * 80)
    lines.append("")
    if data.get('current_environment'):
        lines.append(data['current_environment'])
    else:
        lines.append("The current environment summary provides context for the proposed solution.")
    lines.append("")

    # Section 3: Objectives
    lines.append("3. OBJECTIVES")
    lines.append("-" * 80)
    lines.append("")
    if data.get('objectives'):
        lines.append(data['objectives'])
    else:
        lines.append("• Enhance organizational security posture")
        lines.append("• Achieve and maintain compliance")
        lines.append("• Reduce mean time to detect and respond to incidents")
        lines.append("• Gain visibility into endpoints, networks, and cloud environments")
    lines.append("")

    # Section 4: Scope of Work
    lines.append("4. SCOPE OF WORK")
    lines.append("-" * 80)
    lines.append("")
    lines.append("4.1 Assessment & Design")
    lines.append(data.get('assessment', 'Review existing architecture, identify placement points, define security zones.'))
    lines.append("")
    lines.append("4.2 Implementation")
    lines.append(data.get('implementation', 'Deploy solution components, configure policies, integrate with existing systems.'))
    lines.append("")
    lines.append("4.3 Key Services to be Delivered")
    lines.append(data.get('key_services') or data.get('scope_of_work') or '• Platform deployment and configuration\n• 24/7 security operations\n• Incident response\n• Compliance management')
    lines.append("")

    # Section 5: Solution Proposed
    lines.append("5. SOLUTION PROPOSED")
    lines.append("-" * 80)
    lines.append("")
    if data.get('solution_proposed'):
        lines.append(data['solution_proposed'])
    elif not data.get('technical_solution'):
        lines.append("63SATS proposes a comprehensive cybersecurity solution combining industry-leading security technology with expert managed security services.")
    lines.append("")
    if data.get('technical_solution'):
        lines.append("5.1 Technical Solution Design")
        lines.append("")
        lines.append(data['technical_solution'])
        lines.append("")
    if data.get('bill_of_materials'):
        lines.append("5.2 Bill of Materials")
        lines.append("")
        lines.append(data['bill_of_materials'])
        lines.append("")

    # Section 6: Implementation Plan
    lines.append("6. IMPLEMENTATION PLAN")
    lines.append("-" * 80)
    lines.append("")
    lines.append("6.1 Implementation Approach")
    lines.append("")
    if data.get('implementation_approach'):
        lines.append(data['implementation_approach'])
    else:
        lines.append("• Phase 1: Discovery and Planning\n• Phase 2: Implementation\n• Phase 3: Optimization\n• Phase 4: Operational Handoff")
    lines.append("")
    lines.append("6.2 Implementation Methodology")
    lines.append("")
    if data.get('implementation_methodology'):
        lines.append(data['implementation_methodology'])
    else:
        lines.append("63SATS follows industry-standard methodologies including Agile Project Management and ITIL-aligned Service Management.")
    lines.append("")

    # Section 7: RACI Matrix
    lines.append("7. RACI MATRIX")
    lines.append("-" * 80)
    lines.append("")
    if data.get('raci_matrix'):
        lines.append(data['raci_matrix'])
    else:
        raci_data = [
            ("Activity", "63SATS", "Client"),
            ("Discovery & Assessment", "R", "A"),
            ("Implementation", "R", "A"),
            ("24/7 Monitoring", "R", "I"),
            ("Incident Response", "R", "A"),
            ("Change Management", "R", "A"),
            ("Weekly Reporting", "R", "I"),
        ]
        for row in raci_data:
            lines.append(f"{row[0]:<25} | {row[1]:<15} | {row[2]}")
    lines.append("")
    lines.append("R = Responsible | A = Accountable | C = Consulted | I = Informed")
    lines.append("")

    # Section 8: Assumptions
    lines.append("8. ASSUMPTIONS")
    lines.append("-" * 80)
    lines.append("")
    if data.get('assumptions'):
        lines.append(data['assumptions'])
    else:
        lines.append("• All systems are operational and accessible\n• Network connectivity is available\n• Admin access will be provided\n• Pricing assumes annual commitment")
    lines.append("")

    # Section 9: Dependencies
    lines.append("9. DEPENDENCIES")
    lines.append("-" * 80)
    lines.append("")
    lines.append(data.get('dependencies', '• VPN and network access provisioning\n• Administrative credentials\n• Change approval workflow definition\n• Escalation matrix and contact information'))
    lines.append("")

    # Section 10: Implementation Timeline
    lines.append("10. IMPLEMENTATION TIMELINE")
    lines.append("-" * 80)
    lines.append("")
    if data.get('timeline') or data.get('implementation_timeline'):
        lines.append(data.get('timeline') or data['implementation_timeline'])
    else:
        lines.append("Week 1-2: Discovery and Planning\nWeek 3-4: Implementation\nWeek 5-6: Optimization\nWeek 7-8: Operations Handoff\n\nTotal Implementation: 6-8 weeks")
    lines.append("")

    # Section 11: Expected Outcomes
    lines.append("11. EXPECTED OUTCOMES AND ROI")
    lines.append("-" * 80)
    lines.append("")
    if data.get('expected_outcomes') or data.get('roi'):
        lines.append(data.get('expected_outcomes') or data['roi'])
    else:
        lines.append("• 60% reduction in mean time to detect (MTTD)\n• 70% improvement in incident response times\n• 95% visibility across all assets\n• 24/7/365 security monitoring")
    lines.append("")

    # Section 12: Why 63SATS
    lines.append("12. WHY 63SATS")
    lines.append("-" * 80)
    lines.append("")
    lines.append(data.get('why_63sats') or WHY_63SATS)
    lines.append("")

    # Section 13: Risk & Mitigations
    lines.append("13. RISK & MITIGATIONS")
    lines.append("-" * 80)
    lines.append("")
    lines.append(data.get('risk_mitigations', 'Risk management is an ongoing process throughout the engagement with monthly reviews and incident-based analysis.'))
    lines.append("")

    # Section 14: Conclusion
    lines.append("14. CONCLUSION")
    lines.append("-" * 80)
    lines.append("")
    conclusion = data.get('conclusion') or f"""In today's rapidly evolving threat landscape, organizations need a trusted partner. 63SATS offers a comprehensive solution that addresses your security needs.

We are confident that our proposed solution will deliver significant value to {client_name}, enhancing your security posture and providing peace of mind.

Thank you for considering 63SATS as your cybersecurity partner."""
    lines.append(conclusion)
    lines.append("")

    lines.append("=" * 80)
    lines.append("PROPOSAL PREPARED BY 63SATS")
    lines.append("=" * 80)

    return "\n".join(lines)