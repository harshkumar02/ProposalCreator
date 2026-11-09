"""
Seed script to populate initial proposal types and block libraries.
Run with: python -m app.services.seed_blocks
"""
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine, Base
from app.models.models import (
    ProposalType, BlockLibrary, ProposalBlock, ProposalTemplate
)


def seed_proposal_types(db: Session):
    """Seed initial proposal types."""
    types = [
        {
            "name": "firewall_deployment",
            "display_name": "Firewall Deployment",
            "description": "Network firewall installation and configuration including NGFW, zone-based security, and policy management",
            "keywords": ["firewall", "ngfw", "palo alto", "fortinet", "checkpoint", "zone-based", "fw policy", "network firewall"],
            "industry_tags": ["enterprise", "mid-market", "government"],
            "sort_order": 1
        },
        {
            "name": "ot_asset_visibility",
            "display_name": "OT/ICS Asset Visibility",
            "description": "Operational technology asset discovery and monitoring for ICS/SCADA environments",
            "keywords": ["ot", "ics", "scada", "modbus", "plc", "industrial", "it/ot", "purdue"],
            "industry_tags": ["ot", "ics", "manufacturing", "energy"],
            "sort_order": 2
        },
        {
            "name": "soc",
            "display_name": "SOC Services",
            "description": "Security Operations Center services including 24/7 monitoring, incident response, and threat hunting",
            "keywords": ["soc", "security operations", "24/7 monitoring", "managed security", "incident response"],
            "industry_tags": ["enterprise", "mid-market", "financial", "healthcare"],
            "sort_order": 3
        },
        {
            "name": "siem",
            "display_name": "SIEM Implementation",
            "description": "SIEM deployment, integration, and tuning for log management and security analytics",
            "keywords": ["siem", "splunk", "log management", "arcsight", "correlation"],
            "industry_tags": ["enterprise", "financial", "government"],
            "sort_order": 4
        },
        {
            "name": "vulnerability_assessment",
            "display_name": "Vulnerability Assessment",
            "description": "Vulnerability scanning, penetration testing, and security assessments",
            "keywords": ["vulnerability", "pentest", "penetration test", "cve", "security assessment"],
            "industry_tags": ["enterprise", "mid-market", "government"],
            "sort_order": 5
        },
        {
            "name": "managed_services",
            "display_name": "Managed Security Services",
            "description": "General MSSP services including managed detection and response",
            "keywords": ["managed", "mssp", "outsourced", "24x7", "mdr", "managed detection"],
            "industry_tags": ["enterprise", "mid-market", "smb"],
            "sort_order": 6
        },
        {
            "name": "endpoint_security",
            "display_name": "Endpoint Security",
            "description": "Endpoint detection and response (EDR/XDR) deployment and management",
            "keywords": ["endpoint", "edr", "xdr", "crowdstrike", "carbon black", "sentinelone"],
            "industry_tags": ["enterprise", "mid-market"],
            "sort_order": 7
        },
        {
            "name": "network_security",
            "display_name": "Network Security",
            "description": "Network access control, segmentation, IDS/IPS, and network monitoring",
            "keywords": ["nac", "network access control", "ids", "ips", "network segmentation", "vpn"],
            "industry_tags": ["enterprise", "mid-market", "government"],
            "sort_order": 8
        }
    ]

    for t in types:
        existing = db.query(ProposalType).filter(ProposalType.name == t["name"]).first()
        if not existing:
            pt = ProposalType(**t)
            db.add(pt)

    db.commit()
    print(f"Seeded {len(types)} proposal types")


def seed_block_libraries(db: Session):
    """Seed initial block libraries."""
    libraries = [
        {
            "name": "static",
            "display_name": "Static Blocks",
            "description": "Standard blocks that apply to all proposal types (About Us, Why Us, Legal, etc.)",
            "is_system": True
        },
        {
            "name": "firewall",
            "display_name": "Firewall Blocks",
            "description": "Firewall-specific content blocks for zone-based security proposals",
            "is_system": True
        },
        {
            "name": "ot",
            "display_name": "OT/ICS Blocks",
            "description": "Operational technology and industrial control system content blocks",
            "is_system": True
        },
        {
            "name": "soc",
            "display_name": "SOC Services Blocks",
            "description": "Security Operations Center services content blocks",
            "is_system": True
        },
        {
            "name": "risk",
            "display_name": "Risk & Compliance Blocks",
            "description": "Risk register, compliance mapping, and governance content blocks",
            "is_system": True
        },
        {
            "name": "common",
            "display_name": "Common Blocks",
            "description": "Common proposal sections that can be used across multiple proposal types",
            "is_system": True
        }
    ]

    for lib in libraries:
        existing = db.query(BlockLibrary).filter(BlockLibrary.name == lib["name"]).first()
        if not existing:
            bl = BlockLibrary(**lib)
            db.add(bl)

    db.commit()
    print(f"Seeded {len(libraries)} block libraries")


def seed_static_blocks(db: Session):
    """Seed static content blocks."""
    # Get library IDs
    static_lib = db.query(BlockLibrary).filter(BlockLibrary.name == "static").first()
    common_lib = db.query(BlockLibrary).filter(BlockLibrary.name == "common").first()
    risk_lib = db.query(BlockLibrary).filter(BlockLibrary.name == "risk").first()

    blocks = [
        # Introduction block
        {
            "library_id": static_lib.id,
            "name": "Introduction",
            "block_key": "introduction",
            "content": """# 1. Introduction

## 1.1 About 63SATS

63SATS, driven by the innovative technology of 63 moons technologies ltd., stands as a comprehensive cybersecurity solutions provider catering to the needs of enterprises. Renowned as trailblazers in both digital markets and cybersecurity, we specialize in ensuring top-notch security for Enterprises, Industries & Government sectors.

63SATS brings you internationally recognized products and manages services with a mission to safeguard invaluable assets against the entire spectrum of sophisticated cyber threats. To position our clients as leading models of secure digital entities in India and globally, 63SATS Cybertech Limited as a security consulting & solution providing company has forged strategic partnerships with top-tier security product companies across the globe.

## 1.2 Proposal Overview

This proposal for **{{project_title}}** is submitted to **{{client_name}}** by 63SATS.

{{proposal_overview}}

**Attention:** {{contact_person}}
**Date:** {{date}}
**Proposal No:** {{proposal_no}}""",
            "block_type": "section",
            "required_variables": ["client_name", "project_title", "date"],
            "section_order": 1,
            "subsection_order": 0
        },

        # Why 63SATS block
        {
            "library_id": static_lib.id,
            "name": "Why 63SATS",
            "block_key": "why_63sats",
            "content": """# 12. Why 63SATS

63SATS is the right partner for this engagement because:

## 1. Expertise
   - Team of certified cybersecurity professionals (CISSP, CISM, CEH, OSCP)
   - Extensive experience with enterprise security implementations
   - Deep expertise across multiple security domains
   - Continuous training and knowledge development

## 2. Partnership & Technology
   - Relationships with leading technology vendors
   - Vendor-neutral approach to recommend best-fit solutions
   - Direct access to vendor engineering and support teams
   - Joint go-to-market capabilities

## 3. Customer Focus
   - Dedicated account management
   - Customized service delivery aligned to your needs
   - Flexible engagement models
   - Proven track record with similar organizations
   - Transparent communication and regular updates

## 4. Technology Leadership
   - Cloud-native platform expertise
   - Integration with existing tools and workflows
   - Continuous platform optimization
   - Access to emerging security capabilities

## 5. Value Proposition
   - Competitive and transparent pricing
   - No hidden fees or surprise charges
   - Predictable cost structure (OpEx vs CapEx)
   - Measurable outcomes and ROI
   - Commitment to customer success""",
            "block_type": "section",
            "section_order": 12,
            "subsection_order": 0
        },

        # RACI Matrix block
        {
            "library_id": static_lib.id,
            "name": "RACI Matrix",
            "block_key": "raci_matrix",
            "content": """# 7. RACI Matrix

The following RACI (Responsible, Accountable, Consulted, Informed) matrix defines the roles and responsibilities between 63SATS (MSSP) and the Client for key activities in the engagement.

| Activity | 63SATS | Client |
|----------|--------|--------|
| Discovery & Assessment | R | A |
| Solution Design | R | A |
| Implementation | R | A |
| Configuration | R | A |
| Testing & Validation | R | A |
| User Training | R | A |
| 24/7 Monitoring | R | I |
| Incident Response | R | A |
| Change Management | R | A |
| Weekly Reporting | R | I |
| Monthly Review | R | A |
| Patch Management | R | A |

**R = Responsible (Does the work) | A = Accountable (Final decision maker) | C = Consulted (Provides input) | I = Informed (Notified of outcomes)**""",
            "block_type": "section",
            "section_order": 7,
            "subsection_order": 0
        },

        # Document Control block
        {
            "library_id": static_lib.id,
            "name": "Document Control",
            "block_key": "document_control",
            "content": """---

## Document Control

**Proprietary and Confidential**

This document contains proprietary information of 63SATS Cybertech Limited. This document is intended solely for the use of the entity to which it is addressed and shall not be reproduced, redistributed, or shared with any third party without the prior written consent of 63SATS Cybertech Limited.

The information contained herein is subject to change without notice. © 2024 63SATS Cybertech Limited. All rights reserved.""",
            "block_type": "static",
            "section_order": 99,  # End of document
            "subsection_order": 0
        },

        # Conclusion block
        {
            "library_id": static_lib.id,
            "name": "Conclusion",
            "block_key": "conclusion",
            "content": """# 14. Conclusion

In today's rapidly evolving threat landscape, organizations need a trusted partner. 63SATS offers a comprehensive solution that addresses your security needs, combining cutting-edge technology with expert human analysis.

**{{client_name}}** deserves a security partner who understands your unique challenges, respects your existing investments, and delivers measurable results. We are confident that our proposed solution will:

- Enhance your security posture
- Reduce risk and minimize exposure
- Provide visibility and control
- Enable confident decision-making
- Deliver measurable ROI

**Next Steps:**

1. Schedule a technical deep-dive with our solution architects
2. Review and finalize scope based on your feedback
3. Agree on commercial terms and timeline
4. Begin implementation planning

We look forward to the opportunity to partner with {{client_name}} and demonstrate our commitment to your success.

Thank you for considering 63SATS as your cybersecurity partner.

---

*Proposal prepared by 63SATS Cybertech Limited*
*For questions, contact: {{contact_email}}*""",
            "block_type": "section",
            "section_order": 14,
            "subsection_order": 0
        },

        # Assumptions block
        {
            "library_id": static_lib.id,
            "name": "Assumptions",
            "block_key": "assumptions",
            "content": """# 8. Assumptions

This proposal is based on the following assumptions. Any changes to these assumptions may impact scope, timeline, and commercial terms.

## Infrastructure Assumptions

- All systems are operational and accessible for implementation
- Network connectivity is available for all monitored assets
- Sufficient admin access will be provided for implementation
- Required firewall ports will be opened

## Access & Connectivity Assumptions

- 63SATS will be provided with secure access to the client network
- Administrative access will be provisioned for 63SATS team
- Email and ticketing system integration will be established

## Process Assumptions

- Client will designate primary and secondary points of contact for approvals
- Change approval workflows will be defined within 2 weeks of engagement start
- Maintenance windows will be agreed upon and scheduled in advance
- Client will provide timely responses to approval requests (within 24-48 hours)

## Commercial Assumptions

- Pricing is based on the scope defined in this proposal
- Pricing assumes annual commitment with standard payment terms
- Any scope expansion will be subject to additional charges
- Professional services are quoted separately""",
            "block_type": "section",
            "required_variables": [],
            "section_order": 8,
            "subsection_order": 0
        },

        # Dependencies block
        {
            "library_id": static_lib.id,
            "name": "Dependencies",
            "block_key": "dependencies",
            "content": """# 9. Dependencies

Successful delivery of services is dependent on the following factors:

## Client Dependencies

- VPN and network access provisioning
- Administrative credentials for all systems
- Change approval workflow definition
- Escalation matrix and contact information
- Current configuration backup

## 63SATS Dependencies

- Skilled resources availability
- Tools and platform access
- Vendor support coordination

## External Dependencies

- Network connectivity stability
- Vendor patch availability
- Third-party system integration""",
            "block_type": "section",
            "section_order": 9,
            "subsection_order": 0
        },

        # Timeline block
        {
            "library_id": static_lib.id,
            "name": "Implementation Timeline",
            "block_key": "timeline",
            "content": """# 10. Implementation Timeline

The proposed implementation timeline is as follows:

{{timeline}}

**Week 1-2: Discovery and Planning**
- Environment assessment and asset inventory
- Requirements gathering and validation
- Project kickoff meeting

**Week 3-4: Implementation**
- Component deployment (staged rollout)
- Policy configuration and initial tuning
- Basic integrations and monitoring setup

**Week 5-6: Optimization**
- Fine-tuning and customization
- User training sessions
- Runbook and playbook development

**Week 7-8: Operations Handoff**
- Go-live preparation
- Operational transition
- Final training and documentation

**Total Implementation: {{timeline_weeks|8}} weeks**""",
            "block_type": "section",
            "required_variables": ["timeline", "timeline_weeks"],
            "section_order": 10,
            "subsection_order": 0
        },

        # Expected Outcomes block
        {
            "library_id": static_lib.id,
            "name": "Expected Outcomes",
            "block_key": "expected_outcomes",
            "content": """# 11. Expected Outcomes and ROI

Through this engagement, the client can expect to achieve:

## Security Improvements
- 60% reduction in mean time to detect (MTTD)
- 70% improvement in incident response times
- 95% visibility across all assets
- Proactive threat identification before data breach occurs

## Operational Benefits
- 24/7/365 security monitoring without internal headcount
- Access to enterprise-grade security technology
- Centralized security visibility across all environments
- Automated response capabilities

## Compliance Support
- Continuous compliance monitoring and reporting
- Audit-ready evidence collection
- Policy enforcement and documentation

## Financial Impact
- Reduced security incidents and associated costs
- Predictable security spend (OpEx vs CapEx)
- Avoided costs of building and maintaining in-house SOC

{{expected_outcomes}}""",
            "block_type": "section",
            "required_variables": ["expected_outcomes"],
            "section_order": 11,
            "subsection_order": 0
        }
    ]

    for b in blocks:
        existing = db.query(ProposalBlock).filter(ProposalBlock.block_key == b["block_key"]).first()
        if not existing:
            block = ProposalBlock(**b)
            db.add(block)

    db.commit()
    print(f"Seeded {len(blocks)} static blocks")


def seed_firewall_blocks(db: Session):
    """Seed firewall-specific content blocks."""
    static_lib = db.query(BlockLibrary).filter(BlockLibrary.name == "static").first()
    firewall_lib = db.query(BlockLibrary).filter(BlockLibrary.name == "firewall").first()

    blocks = [
        {
            "library_id": firewall_lib.id,
            "name": "Firewall Scope",
            "block_key": "scope_firewall",
            "content": """# 4.1 Firewall Deployment Scope

## Assessment & Design
- Review existing network architecture and topology
- Identify key placement points for next-generation firewall (NGFW)
- Define security zones and conduits based on business requirements
- Design solution architecture aligned with {{firewall_vendor}} best practices

## Implementation
- Deploy {{fw_model}} at {{site_count}} location(s)
- Configure security policies based on approved zone design
- Integrate with existing network infrastructure
- Establish logging and monitoring feeds

## Configuration
- Zone-based security policy configuration
- Application identification and control
- URL filtering policies
- Threat prevention profiles (malware, exploits, commands)
- SSL/SSH inspection configuration

## Testing & Validation
- End-to-end connectivity testing
- Policy validation
- Logging verification
- Failover testing""",
            "block_type": "subsection",
            "required_variables": ["firewall_vendor", "fw_model", "site_count"],
            "section_order": 4,
            "subsection_order": 1
        },
        {
            "library_id": firewall_lib.id,
            "name": "Firewall Architecture",
            "block_key": "firewall_architecture",
            "content": """# 4.2 Network Architecture

## Zone Design
The proposed architecture implements a zone-based security model:

- **Trusted Zone**: Internal corporate network
- **DMZ Zone**: Public-facing services
- **Guest Zone**: Visitor and contractor access
- **OT Zone**: Industrial control systems (if applicable)

## High Availability
- Active/Passive cluster configuration
- Automatic failover on primary unit failure
- Synchronized policy and session state

## Integration Points
- LDAP/Active Directory for user authentication
- Syslog/SIEM for logging
- SNMP for network management
- DNS/DHCP integration""",
            "block_type": "subsection",
            "section_order": 4,
            "subsection_order": 2
        }
    ]

    for b in blocks:
        existing = db.query(ProposalBlock).filter(ProposalBlock.block_key == b["block_key"]).first()
        if not existing:
            block = ProposalBlock(**b)
            db.add(block)

    db.commit()
    print(f"Seeded {len(blocks)} firewall blocks")


def seed_ot_blocks(db: Session):
    """Seed OT/ICS-specific content blocks."""
    ot_lib = db.query(BlockLibrary).filter(BlockLibrary.name == "ot").first()

    blocks = [
        {
            "library_id": ot_lib.id,
            "name": "OT Scope",
            "block_key": "scope_ot",
            "content": """# 4. OT/ICS Asset Visibility Scope

## Assessment
- Inventory OT assets across {{site_count}} facility/facilities
- Identify network segments and communication patterns
- Map data flows between IT and OT environments
- Assess current monitoring capabilities

## Protocol Coverage
The solution will provide visibility into the following industrial protocols:
{{#each protocols}}
- **{{name}}**: {{description}}
{{/each}}

## ICS/SCADA System Coverage
- PLC programming stations
- HMI workstations
- Historian servers
- Data gateways
- Engineering workstations

## Key Deliverables
- Complete asset inventory report
- Network topology diagram
- Communication matrix
- Risk assessment report
- Monitoring deployment plan""",
            "block_type": "section",
            "required_variables": ["site_count", "protocols"],
            "condition_expression": "protocols and 'ot' in industry_tags",
            "section_order": 4,
            "subsection_order": 1
        },
        {
            "library_id": ot_lib.id,
            "name": "OT Assumptions",
            "block_key": "ot_assumptions",
            "content": """## OT-Specific Assumptions

- All OT systems are operational and accessible during agreed maintenance windows
- Network segmentation (DMZ) is in place between IT and OT environments
- PLC and control device access will be coordinated with operations team
- Passive monitoring only (no active scanning of production OT systems)
- Maintenance windows will be scheduled during planned production downtime
- Separate credentials will be provided for OT system access
- Change management process for OT environment will be followed
- Rollback procedures will be defined before any changes
- Operations team will be available during implementation phases""",
            "block_type": "subsection",
            "condition_expression": "protocols and 'ot' in industry_tags",
            "section_order": 8,
            "subsection_order": 5
        },
        {
            "library_id": ot_lib.id,
            "name": "Purdue Model",
            "block_key": "purdue_model",
            "content": """## OT Security Reference Architecture

The proposed solution aligns with the Purdue Enterprise Reference Architecture:

**Level 5 - Enterprise Zone**
- Business planning and logistics
- Standard security controls apply

**Level 4 - Business Planning**
- ERP, historians, engineering workstations
- Standard IT security controls

**Level 3 - Operations Management**
- Operations managers, batch management
- Enhanced monitoring and control

**Level 3.5 - DMZ (IT/OT Boundary)**
- Demilitarized zone between IT and OT
- Firewall/IDS at boundary
- Data diodes where required

**Level 2 - Supervisory Control**
- HMI, SCADA servers
- Passive monitoring only
- Enhanced logging

**Level 1 - Basic Control**
- PLCs, RTUs
- Read-only access
- No modifications

**Level 0 - Field Devices**
- Sensors, actuators
- No direct connectivity""",
            "block_type": "subsection",
            "condition_expression": "protocols and 'ot' in industry_tags",
            "section_order": 5,
            "subsection_order": 1
        }
    ]

    for b in blocks:
        existing = db.query(ProposalBlock).filter(ProposalBlock.block_key == b["block_key"]).first()
        if not existing:
            block = ProposalBlock(**b)
            db.add(block)

    db.commit()
    print(f"Seeded {len(blocks)} OT blocks")


def seed_soc_blocks(db: Session):
    """Seed SOC services content blocks."""
    soc_lib = db.query(BlockLibrary).filter(BlockLibrary.name == "soc").first()

    blocks = [
        {
            "library_id": soc_lib.id,
            "name": "SOC Scope",
            "block_key": "scope_soc",
            "content": """# 4. SOC Services Scope

## 24/7 Security Operations Center

### Monitoring Capabilities
- {{monitoring_hours|24x7x365}} security monitoring
- Real-time threat detection and alerting
- Correlation of events across multiple data sources
- Behavioral analysis and anomaly detection

### Coverage
- Network traffic analysis
- Endpoint telemetry monitoring
- Cloud workload protection
- Email and collaboration security
- User behavior analytics

### SOC Team Structure
- Tier 1: First-line analysts (24/7)
- Tier 2: Senior analysts (business hours + on-call)
- Tier 3: Threat hunting specialists
- SOC Manager: Engagement oversight

### Tools & Technology
- SIEM platform: {{siem_platform}}
- SOAR automation
- Threat intelligence feeds
- Custom detection rules""",
            "block_type": "section",
            "required_variables": ["monitoring_hours", "siem_platform"],
            "section_order": 4,
            "subsection_order": 1
        },
        {
            "library_id": soc_lib.id,
            "name": "SOC Escalation",
            "block_key": "soc_escalation",
            "content": """## Escalation Matrix

| Severity | Definition | Response Time | Escalation |
|----------|------------|---------------|------------|
| Critical | Active breach, data exfiltration | 15 minutes | Immediate |
| High | Confirmed malware, attempted breach | 1 hour | 4 hours |
| Medium | Suspicious activity | 4 hours | 24 hours |
| Low | Policy violation, informational | 24 hours | 72 hours |

### Contact Requirements
- Primary contact: {{primary_contact}}
- Secondary contact: {{secondary_contact}}
- Emergency hotline: {{emergency_number}}""",
            "block_type": "subsection",
            "required_variables": ["primary_contact", "secondary_contact", "emergency_number"],
            "section_order": 7,
            "subsection_order": 1
        },
        {
            "library_id": soc_lib.id,
            "name": "SOC SLA",
            "block_key": "soc_sla",
            "content": """## Service Level Agreement

### Response Time Guarantees

| Metric | Target |
|--------|--------|
| MTTD (Mean Time to Detect) | < 15 minutes |
| MTTR (Mean Time to Respond) | < 30 minutes |
| Alert Acknowledgment | < 5 minutes |
| False Positive Rate | < 5% |

### Reporting
- Weekly status report
- Monthly executive summary
- Quarterly business review
- Incident post-mortem reports

### Continuous Improvement
- Weekly threat hunting sessions
- Monthly detection rule tuning
- Quarterly platform review
- Annual technology assessment""",
            "block_type": "subsection",
            "section_order": 11,
            "subsection_order": 2
        }
    ]

    for b in blocks:
        existing = db.query(ProposalBlock).filter(ProposalBlock.block_key == b["block_key"]).first()
        if not existing:
            block = ProposalBlock(**b)
            db.add(block)

    db.commit()
    print(f"Seeded {len(blocks)} SOC blocks")


def seed_risk_blocks(db: Session):
    """Seed risk management content blocks."""
    risk_lib = db.query(BlockLibrary).filter(BlockLibrary.name == "risk").first()

    blocks = [
        {
            "library_id": risk_lib.id,
            "name": "Risk Register",
            "block_key": "risk_register",
            "content": """# 13. Risk & Mitigations

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Network downtime during implementation | Medium | High | Staged rollout with rollback capability |
| Firewall rule conflicts | Low | Medium | Thorough testing in dev environment |
| Integration issues with existing systems | Medium | Medium | Detailed discovery phase |
| OT system compatibility issues | Medium | High | Passive monitoring only, coordinated changes |
| Delayed access provisioning | High | Medium | Early access request, escalate blockers |

## Risk Monitoring
- Weekly risk review meetings
- Monthly risk register update
- Real-time alerting on risk indicators
- Quarterly risk assessment reports

## Business Continuity
- Rollback procedures documented
- Change management process
- Escalation matrix defined
- Communication plan in place""",
            "block_type": "section",
            "section_order": 13,
            "subsection_order": 0
        }
    ]

    for b in blocks:
        existing = db.query(ProposalBlock).filter(ProposalBlock.block_key == b["block_key"]).first()
        if not existing:
            block = ProposalBlock(**b)
            db.add(block)

    db.commit()
    print(f"Seeded {len(blocks)} risk blocks")


def run_seed():
    """Run all seeding functions."""
    print("Starting seed process...")

    # Create tables
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        seed_proposal_types(db)
        seed_block_libraries(db)
        seed_static_blocks(db)
        seed_firewall_blocks(db)
        seed_ot_blocks(db)
        seed_soc_blocks(db)
        seed_risk_blocks(db)
        print("Seed complete!")
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()