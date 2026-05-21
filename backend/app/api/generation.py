from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import json
import io

from app.core.database import get_db
from app.models.models import Proposal, Template, User, ExtractionResult
from app.api.auth import get_current_user
from app.services.document_generator import generate_proposal_document, apply_template_with_placeholders

router = APIRouter()


# Fixed content
ABOUT_63SATS = """63SATS is a leading Cybersecurity SI/MSSP provider specializing in comprehensive security solutions. We help organizations protect their digital assets through cutting-edge technology, expert analysis, and proactive threat management.

With a focus on innovation and customer success, 63SATS provides end-to-end cybersecurity services including:

• 24/7 Security Operations Center (SOC) monitoring
• Incident Response and Threat Hunting
• Compliance Management (SOC2, ISO 27001, GDPR, HIPAA, PCI-DSS)
• Security Awareness Training
• Vulnerability Management
• Endpoint Detection and Response (EDR)
• Cloud Security Posture Management
• Network Security Solutions

Our team of certified security professionals brings decades of combined experience in cybersecurity, having protected organizations across financial services, healthcare, government, and enterprise sectors."""

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

    # Prepare extracted data
    extracted_data = {}
    if proposal.extracted_data:
        try:
            extracted_data = json.loads(proposal.extracted_data)
        except json.JSONDecodeError:
            extracted_data = {"raw_data": proposal.extracted_data}

    # If RFP is linked, get extraction results
    if proposal.rfp_id:
        results = db.query(ExtractionResult).filter(
            ExtractionResult.rfp_id == proposal.rfp_id,
            ExtractionResult.is_reviewed == True
        ).all()
        for r in results:
            if r.value:
                extracted_data[r.field_name] = r.value

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

    # Prepare extracted data
    extracted_data = {}
    if proposal.extracted_data:
        try:
            extracted_data = json.loads(proposal.extracted_data)
        except json.JSONDecodeError:
            extracted_data = {"raw_data": proposal.extracted_data}

    # If RFP is linked, get extraction results
    if proposal.rfp_id:
        results = db.query(ExtractionResult).filter(
            ExtractionResult.rfp_id == proposal.rfp_id
        ).all()
        for r in results:
            if r.value:
                extracted_data[r.field_name] = r.value

    # Generate text from template
    if template and template.content:
        text = apply_template_with_placeholders(template.content, extracted_data)
    else:
        # Generate from extracted data directly using 63SATS format
        text = generate_63sats_proposal_text(extracted_data, proposal.client_name)

    return {"text": text}


def generate_63sats_proposal_text(data: dict, client_name: str) -> str:
    """Generate a 63SATS formatted proposal text."""
    lines = []

    # Title
    lines.append("=" * 70)
    lines.append("63SATS - CYBERSECURITY SERVICES PROPOSAL")
    lines.append("=" * 70)
    lines.append("")

    # Section 1: Introduction
    lines.append("1. INTRODUCTION")
    lines.append("-" * 70)
    lines.append("")
    lines.append("1.1 About 63SATS")
    lines.append("")
    lines.append(ABOUT_63SATS)
    lines.append("")

    lines.append("1.2 Proposal Overview")
    lines.append("")
    overview = f"This proposal is submitted by 63SATS in response to the Request for Proposal from {client_name}."
    if data.get('project_title'):
        overview += f"\n\nProject: {data['project_title']}"
    lines.append(overview)
    lines.append("")

    # Section 2: Current Challenges
    lines.append("2. CURRENT CHALLENGES")
    lines.append("-" * 70)
    lines.append("")
    if data.get('current_challenges'):
        lines.append(data['current_challenges'])
    else:
        lines.append("Organizations today face an evolving landscape of cybersecurity threats including increasing sophistication of cyber attacks, shortage of skilled security professionals, and complex compliance requirements.")
    lines.append("")

    # Section 3: Objectives
    lines.append("3. OBJECTIVES")
    lines.append("-" * 70)
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
    lines.append("-" * 70)
    lines.append("")
    lines.append("4.1 Assets")
    lines.append("")
    if data.get('assets'):
        lines.append(data['assets'])
    else:
        lines.append("• Endpoints (Workstations, Servers, Mobile devices)")
        lines.append("• Infrastructure (On-premises, Cloud environments)")
        lines.append("• Applications (Business applications, SaaS services)")
    lines.append("")

    lines.append("4.2 Key Services to be Delivered")
    lines.append("")
    if data.get('key_services'):
        lines.append(data['key_services'])
    else:
        lines.append("• Platform Deployment & Configuration")
        lines.append("• 24/7 Security Operations")
        lines.append("• Incident Response")
        lines.append("• Compliance Management")
        lines.append("• Reporting & Communication")
    lines.append("")

    # Section 5: Solution Proposed
    lines.append("5. SOLUTION PROPOSED")
    lines.append("-" * 70)
    lines.append("")
    if data.get('solution_proposed'):
        lines.append(data['solution_proposed'])
    else:
        lines.append("63SATS proposes a comprehensive cybersecurity solution combining industry-leading security technology with our expert managed security services.")
        lines.append("")
        lines.append("Key Components:")
        lines.append("1. Security Platform - AI-powered endpoint protection")
        lines.append("2. 63SATS Managed Services - Expert security analysts 24/7")
        lines.append("3. Integration & Automation - Custom detection rules and SOAR playbooks")
    lines.append("")

    # Section 6: Implementation Plan
    lines.append("6. IMPLEMENTATION PLAN")
    lines.append("-" * 70)
    lines.append("")
    lines.append("6.1 Implementation Approach")
    lines.append("")
    if data.get('implementation_approach'):
        lines.append(data['implementation_approach'])
    else:
        lines.append("• Phase 1: Discovery and Planning")
        lines.append("• Phase 2: Platform Deployment")
        lines.append("• Phase 3: Optimization and Tuning")
        lines.append("• Phase 4: Operational Handoff")
    lines.append("")

    lines.append("6.2 Implementation Methodology")
    lines.append("")
    if data.get('implementation_methodology'):
        lines.append(data['implementation_methodology'])
    else:
        lines.append("63SATS follows industry-standard implementation methodologies including Agile Project Management and ITIL-aligned Service Management.")
    lines.append("")

    # Section 7: RACI Matrix
    lines.append("7. RACI MATRIX")
    lines.append("-" * 70)
    lines.append("")
    lines.append("R = Responsible | A = Accountable | C = Consulted | I = Informed")
    lines.append("")
    raci_data = [
        ("Activity", "63SATS", "Client"),
        ("Discovery & Assessment", "R", "A"),
        ("Platform Deployment", "R", "A"),
        ("Agent Installation", "C", "R/A"),
        ("24/7 Monitoring", "R", "I"),
        ("Incident Response", "R", "A"),
        ("Weekly Reporting", "R", "I"),
        ("Quarterly Reviews", "R", "A"),
    ]
    for row in raci_data:
        lines.append(f"{row[0]:<25} | {row[1]:<15} | {row[2]}")
    lines.append("")

    # Section 8: Assumptions
    lines.append("8. ASSUMPTIONS")
    lines.append("-" * 70)
    lines.append("")
    if data.get('assumptions'):
        lines.append(data['assumptions'])
    else:
        lines.append("• Client has or will procure necessary security platform licenses")
        lines.append("• Sufficient admin access will be provided for implementation")
        lines.append("• Primary point of contact will be available during implementation")
    lines.append("")

    # Section 9: Implementation Timeline
    lines.append("9. IMPLEMENTATION TIMELINE")
    lines.append("-" * 70)
    lines.append("")
    if data.get('timeline'):
        lines.append(data['timeline'])
    else:
        lines.append("Week 1-2: Discovery and Planning")
        lines.append("Week 3-4: Platform Deployment")
        lines.append("Week 5-6: Optimization")
        lines.append("Week 7+: Operations")
        lines.append("")
        lines.append("Total Implementation: 6-8 weeks")
    lines.append("")

    # Section 10: Expected Outcomes
    lines.append("10. EXPECTED OUTCOMES AND ROI")
    lines.append("-" * 70)
    lines.append("")
    if data.get('expected_outcomes'):
        lines.append(data['expected_outcomes'])
    else:
        lines.append("• 60% reduction in mean time to detect (MTTD)")
        lines.append("• 70% improvement in incident response times")
        lines.append("• 95% endpoint visibility across all assets")
        lines.append("• 24/7/365 security monitoring without internal headcount")
    lines.append("")

    # Section 11: Why 63SATS
    lines.append("11. WHY 63SATS")
    lines.append("-" * 70)
    lines.append("")
    lines.append(WHY_63SATS)
    lines.append("")

    # Section 12: Conclusion
    lines.append("12. CONCLUSION")
    lines.append("-" * 70)
    lines.append("")
    conclusion = f"""In today's rapidly evolving threat landscape, organizations need a trusted partner to help them navigate cybersecurity challenges. 63SATS offers a comprehensive solution that addresses your security needs while enabling your team to focus on core business objectives.

We are confident that our proposed solution will deliver significant value to {client_name}, enhancing your security posture and providing peace of mind.

We look forward to the opportunity to partner with you and demonstrate our commitment to your success.

Thank you for considering 63SATS as your cybersecurity partner."""
    lines.append(conclusion)
    lines.append("")

    lines.append("=" * 70)
    lines.append("PROPOSAL PREPARED BY 63SATS")
    lines.append("=" * 70)

    return "\n".join(lines)