from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import re
from typing import Dict, Optional, List
import io


# Fixed content for 63SATS proposals (same for all)
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


CONCLUSION = """In today's rapidly evolving threat landscape, organizations need a trusted partner to help them navigate cybersecurity challenges. 63SATS offers a comprehensive solution that addresses your security needs while enabling your team to focus on core business objectives.

We are confident that our proposed solution will deliver significant value to your organization, enhancing your security posture and providing peace of mind.

We look forward to the opportunity to partner with you and demonstrate our commitment to your success.

For any questions regarding this proposal, please don't hesitate to contact us.

Thank you for considering 63SATS as your cybersecurity partner."""


def generate_proposal_document(
    template_content: Optional[str],
    extracted_data: Dict,
    output_filename: str = "proposal.docx"
) -> bytes:
    """
    Generate a Word document following the 63SATS proposal format.
    """
    doc = Document()

    # Style the document
    style = doc.styles['Normal']
    style.font.name = 'Calibri'
    style.font.size = Pt(11)

    # ============================================
    # SECTION 1: INTRODUCTION
    # ============================================

    # 1.1 About 63SATS
    doc.add_heading('1. Introduction', 0)
    doc.add_heading('1.1 About 63SATS', level=1)
    doc.add_paragraph(ABOUT_63SATS)

    # 1.2 Proposal Overview
    doc.add_heading('1.2 Proposal Overview', level=1)
    client_name = extracted_data.get('client_name', '[Client Name]')
    project_title = extracted_data.get('project_title', '[Project Title]')

    overview = f"""This proposal is submitted by 63SATS in response to the Request for Proposal (RFP) from {client_name}.

Project: {project_title}

This document outlines our understanding of your requirements, our proposed solution, implementation approach, and the value we bring to your organization."""
    doc.add_paragraph(overview)

    # ============================================
    # SECTION 2: CURRENT CHALLENGES
    # ============================================
    doc.add_heading('2. Current Challenges', level=1)
    current_challenges = extracted_data.get('current_challenges', '''
Organizations today face an evolving landscape of cybersecurity threats. Common challenges include:

• Increasing sophistication of cyber attacks and advanced persistent threats (APTs)
• Shortage of skilled security professionals
• Complex compliance requirements (SOC2, ISO27001, GDPR, HIPAA, PCI-DSS)
• Managing multiple security tools and vendors
• Limited visibility into endpoint and network activities
• Slow incident response times leading to extended dwell time
• Legacy system vulnerabilities and technical debt
• Cloud security misconfigurations

These challenges require a comprehensive, integrated approach to security that many organizations struggle to implement and maintain internally.''')
    doc.add_paragraph(current_challenges)

    # ============================================
    # SECTION 3: OBJECTIVES
    # ============================================
    doc.add_heading('3. Objectives', level=1)
    objectives = extracted_data.get('objectives', '''
The primary objectives of this engagement are:

1. Enhance organizational security posture through comprehensive monitoring and protection
2. Achieve and maintain compliance with relevant regulatory frameworks
3. Reduce mean time to detect (MTTD) and mean time to respond (MTTR) to security incidents
4. Gain complete visibility into endpoints, networks, and cloud environments
5. Enable proactive threat hunting and intelligence-led security operations
6. Build internal security awareness and capabilities through knowledge transfer
7. Establish incident response procedures and playbooks
8. Provide transparent reporting and metrics demonstrating security improvements''')
    doc.add_paragraph(objectives)

    # ============================================
    # SECTION 4: SCOPE OF WORK
    # ============================================
    doc.add_heading('4. Scope of Work', level=1)

    # 4.1 Assets
    doc.add_heading('4.1 Assets', level=2)
    assets = extracted_data.get('assets', '''
The scope of this engagement covers the following assets:

Endpoints:
• Workstations and laptops (Windows, macOS, Linux)
• Physical and virtual servers (Windows Server, Linux)
• Mobile devices (iOS, Android)

Infrastructure:
• On-premises data centers
• Cloud environments (AWS, Azure, GCP)
• Network perimeter devices
• Active Directory / Identity systems

Applications:
• Critical business applications
• Cloud SaaS services
• Custom-developed applications
• Databases and data stores''')
    doc.add_paragraph(assets)

    # 4.2 Key Services
    doc.add_heading('4.2 Key Services to be Delivered', level=2)
    services_default = '''
The following services will be delivered as part of this engagement:

1. Platform Deployment & Configuration
   • Security platform deployment and agent installation
   • Policy configuration and optimization
   • Integration with existing security tools
   • Baseline establishment

2. 24/7 Security Operations
   • Continuous monitoring and alerting
   • Incident detection and triage
   • Threat hunting activities
   • Security analyst support

3. Incident Response
   • Rapid incident investigation
   • Containment and remediation guidance
   • Forensic analysis and evidence collection
   • Post-incident analysis and reporting

4. Compliance Management
   • Compliance monitoring and reporting
   • Audit support and evidence gathering
   • Policy documentation and updates
   • Gap assessment and remediation tracking

5. Reporting & Communication
   • Weekly security reports
   • Monthly executive summaries
   • Quarterly business reviews
   • Ad-hoc reporting as required'''
    services = extracted_data.get('key_services') or extracted_data.get('requirements') or extracted_data.get('deliverables') or services_default
    doc.add_paragraph(services)

    # ============================================
    # SECTION 5: SOLUTION PROPOSED
    # ============================================
    doc.add_heading('5. Solution Proposed', level=1)
    solution = extracted_data.get('solution_proposed', '''
63SATS proposes a comprehensive cybersecurity solution combining industry-leading security technology with our expert managed security services.

Key Components:

1. Security Platform
   • AI-powered endpoint protection
   • Real-time threat intelligence
   • Cloud-native architecture
   • Unified visibility across all endpoints and environments

2. 63SATS Managed Services
   • Expert security analysts monitoring 24/7/365
   • Proactive threat hunting
   • Incident response coordination
   • Compliance reporting and support

3. Integration & Automation
   • Seamless integration with existing tools
   • Automated response workflows
   • Custom detection rules tailored to your environment
   • SOAR playbook development and implementation''')
    doc.add_paragraph(solution)

    # ============================================
    # SECTION 6: IMPLEMENTATION PLANNED
    # ============================================
    doc.add_heading('6. Implementation Plan', level=1)

    # 6.1 Implementation Approach
    doc.add_heading('6.1 Implementation Approach', level=2)
    approach = extracted_data.get('implementation_approach', '''
Our implementation follows a structured, phased approach designed to minimize disruption and ensure successful deployment:

Phase 1: Discovery and Planning
• Assess current environment and inventory all assets
• Define success criteria and key performance indicators
• Develop detailed project timeline and resource plan
• Identify stakeholders and communication requirements

Phase 2: Platform Deployment
• Deploy security agents across endpoints (staged rollout)
• Configure policies and protection settings
• Integrate with existing SIEM/SOAR tools
• Establish data feeds and alerting channels

Phase 3: Optimization and Tuning
• Fine-tune detection rules and alerting thresholds
• Configure baseline behaviors for your environment
• Develop custom detection use cases
• Create runbooks and playbooks

Phase 4: Operational Handoff
• Train client team on platform usage and reporting
• Document procedures and operational runbooks
• Establish communication protocols and escalation paths
• Transition to steady-state operations''')
    doc.add_paragraph(approach)

    # 6.2 Implementation Methodology
    doc.add_heading('6.2 Implementation Methodology', level=2)
    methodology = extracted_data.get('implementation_methodology', '''
63SATS follows industry-standard implementation methodologies:

• Agile Project Management: Iterative approach with regular checkpoints and flexibility for scope adjustments
• ITIL-aligned Service Management: Best practices for service delivery and incident management
• Industry Best Practices: Proven deployment methodologies refined through numerous implementations
• Collaborative Approach: Regular communication with stakeholder feedback at each milestone

Project Governance:
• Weekly status meetings with project team
• Bi-weekly steering committee updates
• Documented change management process
• Risk and issue tracking with mitigation plans
• Quality assurance checkpoints''')
    doc.add_paragraph(methodology)

    # ============================================
    # SECTION 7: RACI MATRIX
    # ============================================
    doc.add_heading('7. RACI Matrix', level=1)

    raci_intro = '''The following RACI matrix defines responsibilities during the implementation and ongoing operations phases:

R = Responsible (Does the work) | A = Accountable (Final decision maker) | C = Consulted (Provides input) | I = Informed (Notified of outcomes)'''
    doc.add_paragraph(raci_intro)

    # Create RACI table
    raci_data = [
        ['Activity', '63SATS', 'Client'],
        ['Discovery & Assessment', 'R', 'A'],
        ['Solution Design', 'R', 'A'],
        ['Platform Deployment', 'R', 'A'],
        ['Agent Installation', 'C', 'R/A'],
        ['Policy Configuration', 'R', 'A'],
        ['Integration Setup', 'R', 'A'],
        ['Testing & Validation', 'R', 'A'],
        ['User Training', 'R', 'A'],
        ['24/7 Monitoring', 'R', 'I'],
        ['Incident Response', 'R', 'A'],
        ['Weekly Reporting', 'R', 'I'],
        ['Quarterly Reviews', 'R', 'A'],
        ['Platform Updates', 'R', 'I'],
        ['Change Management', 'C', 'R/A'],
    ]

    table = doc.add_table(rows=len(raci_data), cols=3)
    table.style = 'Table Grid'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    # Fill table
    for i, row_data in enumerate(raci_data):
        row = table.rows[i]
        for j, cell_text in enumerate(row_data):
            cell = row.cells[j]
            cell.text = cell_text
            # Make header row bold
            if i == 0:
                cell.paragraphs[0].runs[0].bold = True
                # Add shading to header
                shading = OxmlElement('w:shd')
                shading.set(qn('w:fill'), 'E0E0E0')
                cell._tc.get_or_add_tcPr().append(shading)

    # ============================================
    # SECTION 8: ASSUMPTIONS
    # ============================================
    doc.add_heading('8. Assumptions', level=1)
    assumptions_default = '''
The following assumptions apply to this proposal:

1. Technical Assumptions
   • Client has or will procure necessary security platform licenses
   • Endpoints are reachable for agent deployment
   • Network connectivity is available for all monitored assets
   • Sufficient admin access will be provided for implementation
   • Required firewall ports will be opened

2. Organizational Assumptions
   • Primary point of contact will be available during implementation
   • IT team will participate in training sessions
   • Stakeholders will provide timely feedback on deliverables
   • Decision-making authority is available when needed

3. Commercial Assumptions
   • Pricing is valid for 30 days from proposal date
   • Services will commence upon contract execution
   • Annual contract term with monthly billing
   • Volume pricing based on agreed endpoint count

4. Scope Limitations
   • On-site support requires separate engagement
   • Custom development requires separate Statement of Work
   • Physical security assessments excluded
   • Application security testing requires separate engagement'''
    assumptions = extracted_data.get('assumptions') or extracted_data.get('terms_and_conditions') or assumptions_default
    doc.add_paragraph(assumptions)

    # ============================================
    # SECTION 9: IMPLEMENTATION TIMELINE
    # ============================================
    doc.add_heading('9. Implementation Timeline', level=1)
    timeline_default = '''
The proposed implementation timeline is as follows:

Week 1-2: Discovery and Planning
• Environment assessment and asset inventory
• Requirements gathering and validation
• Project kickoff meeting
• Security platform procurement (if applicable)

Week 3-4: Platform Deployment
• Agent deployment (staged rollout across departments)
• Policy configuration and initial tuning
• Basic integrations with existing tools
• Initial alerting and monitoring setup

Week 5-6: Optimization
• Fine-tuning and customization
• User training sessions
• Runbook and playbook development
• Integration completion

Week 7-8: Operations Handoff
• Go-live preparation
• Operational transition
• Final training and documentation
• Steady-state operations begins

Total Implementation: 6-8 weeks

Key Milestones:
• M1: Project Kickoff - Week 1
• M2: Deployment Complete - Week 4
• M3: Optimization Complete - Week 6
• M4: Full Operations - Week 8'''
    timeline = extracted_data.get('implementation_timeline') or extracted_data.get('timeline') or timeline_default
    doc.add_paragraph(timeline)

    # ============================================
    # SECTION 10: EXPECTED OUTCOMES AND ROI
    # ============================================
    doc.add_heading('10. Expected Outcomes and ROI', level=1)
    roi_default = '''
Through this engagement, the client can expect to achieve:

1. Security Improvements
   • 60% reduction in mean time to detect (MTTD)
   • 70% improvement in incident response times
   • 95% endpoint visibility across all assets
   • Proactive threat identification before data breach occurs
   • Reduced alert fatigue through intelligent prioritization

2. Operational Benefits
   • 24/7/365 security monitoring without internal headcount
   • Access to enterprise-grade security technology
   • Centralized security visibility across all environments
   • Automated response capabilities
   • Reduced complexity from consolidated tools

3. Compliance Support
   • Continuous compliance monitoring and reporting
   • Audit-ready evidence collection
   • Policy enforcement and documentation
   • Support for SOC2, ISO27001, HIPAA, PCI-DSS, and other frameworks

4. Financial Impact
   • Reduced security incidents and associated costs
   • Predictable security spend (OpEx vs CapEx)
   • Avoided costs of building and maintaining in-house SOC
   • Potential reduction in cyber insurance premiums'''
    roi = extracted_data.get('expected_outcomes') or extracted_data.get('roi') or roi_default
    doc.add_paragraph(roi)

    # ============================================
    # SECTION 11: WHY 63SATS
    # ============================================
    doc.add_heading('11. Why 63SATS', level=1)
    doc.add_paragraph(WHY_63SATS)

    # ============================================
    # SECTION 12: CONCLUSION
    # ============================================
    doc.add_heading('12. Conclusion', level=1)
    conclusion = CONCLUSION.replace("your organization", client_name)
    doc.add_paragraph(conclusion)

    # Contact information
    doc.add_paragraph()
    contact = doc.add_paragraph()
    contact.add_run('\n\n--- PROPOSAL PREPARED BY 63SATS ---').bold = True
    contact.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Save to bytes
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


def apply_template_with_placeholders(template_content: str, extracted_data: Dict) -> str:
    """Replace {{placeholder}} tags in template with actual values."""
    result = template_content

    for key, value in extracted_data.items():
        placeholder = f"{{{{{key}}}}}"
        if value:
            result = result.replace(placeholder, str(value))
        else:
            result = result.replace(placeholder, '[Not Provided]')

    return result


def create_template_from_content(content: str) -> str:
    """Create a template document from Word content."""
    doc = Document(io.BytesIO(content))
    text_content = []

    for para in doc.paragraphs:
        if para.text.strip():
            text_content.append(para.text)

    return '\n\n'.join(text_content)


def extract_placeholders_from_template(content: str) -> list:
    """Extract all {{placeholder}} patterns from template content."""
    pattern = r'\{\{([^}]+)\}\}'
    return re.findall(pattern, content)