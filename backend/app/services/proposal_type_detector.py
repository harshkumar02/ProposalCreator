from typing import Dict, List, Tuple, Optional
import re
from app.core.config import settings


# Keyword mappings for proposal types
PROPOSAL_TYPE_KEYWORDS = {
    "firewall_deployment": [
        "firewall", "ngfw", "next generation firewall", "palo alto", "fortinet",
        "checkpoint", "zone-based", "security zone", "fw policy", "network firewall",
        "unified threat management", "utm", "stateful firewall", "packet filtering"
    ],
    "ot_asset_visibility": [
        "ot", "operational technology", "ics", "scada", "industrial control",
        "plc", "modbus", "profinet", "ethernet/ip", "plant floor", "hmi",
        "industrial ethernet", "scada system", "process automation", "dcs",
        "distributed control", "instrumentation", "control system", "it/ot"
    ],
    "soc": [
        "soc", "security operations center", "24/7 monitoring", "security monitoring",
        "managed security", "security analyst", "tier 1", "tier 2", "tier 3",
        "alert monitoring", "incident response", "threat hunting", "soc operations"
    ],
    "siem": [
        "siem", "splunk", "arcsight", "log management", "security information",
        "log analysis", "correlation rule", "splunk enterprise", "qradar",
        "microsoft sentinel", "log analytics", "security event", "log collection"
    ],
    "vulnerability_assessment": [
        "vulnerability", "va", "penetration", "pentest", "vuln scan", "cve",
        "vulnerability scan", "security assessment", "risk assessment",
        "penetration test", "ethical hacking", "security testing", "appsec"
    ],
    "managed_services": [
        "managed", "mssp", "outsourced", "managed security", "24x7", "24/7",
        "managed detection", "managed response", "co-managed", "hybrid soc",
        "security outsourcing", "mdr", "managed threat"
    ],
    "endpoint_security": [
        "endpoint", "edr", "xdr", "antivirus", "carbon black", "crowdstrike",
        "sentinelone", "defender", "malware", "ransomware protection",
        "endpoint detection", "workload protection", "device control"
    ],
    "cloud_security": [
        "cloud security", "casb", "cspm", "cwpp", "cloud posture",
        "aws security", "azure security", "gcp security", "cloud protection",
        "cloud workload", "cloud access", "devsecops", "infrastructure as code"
    ],
    "network_security": [
        "network security", "nac", "network access control", "ids", "ips",
        "intrusion detection", "intrusion prevention", "wireless security",
        "vpn", "network segmentation", "microsegmentation"
    ],
    "compliance": [
        "compliance", "iso 27001", "pci dss", "hipaa", "gdpr", "soc 2",
        "nist", "framework", "audit", "regulatory", "certification",
        "pci compliance", "data protection", "privacy"
    ]
}


def detect_proposal_type(extracted_data: Dict, rfp_content: str = None) -> Tuple[str, float, Dict]:
    """
    Detect proposal type using keyword matching + AI analysis.

    Args:
        extracted_data: Dictionary of extracted field values from RFP
        rfp_content: Optional raw RFP text for additional analysis

    Returns:
        Tuple of (proposal_type_name, confidence_score, metadata_dict)
    """
    # Build search text from extracted data
    search_text = _build_search_text(extracted_data, rfp_content)
    search_text_lower = search_text.lower()

    scores = {}
    matched_keywords = {}

    for ptype, keywords in PROPOSAL_TYPE_KEYWORDS.items():
        score = 0
        found_keywords = []
        for kw in keywords:
            if kw.lower() in search_text_lower:
                score += 1
                found_keywords.append(kw)
        scores[ptype] = score
        matched_keywords[ptype] = found_keywords

    # Find best match
    if not scores or max(scores.values()) == 0:
        return "managed_services", 0.3, {"source": "keyword", "reason": "No specific type detected, defaulting to managed_services"}

    best_type = max(scores, key=scores.get)
    max_score = scores[best_type]

    # Normalize confidence (3+ keyword matches = high confidence)
    confidence = min(max_score / 3.0, 1.0)

    metadata = {
        "source": "keyword",
        "matched_keywords": matched_keywords[best_type],
        "all_scores": scores
    }

    # AI-assisted detection for ambiguous cases (confidence < 0.5)
    if confidence < 0.5 and settings.ANTHROPIC_API_KEY:
        ai_type, ai_conf, ai_metadata = _ai_assist_detection(extracted_data, rfp_content)
        if ai_conf > confidence:
            return ai_type, ai_conf, {**ai_metadata, "fallback_type": best_type}

    return best_type, confidence, metadata


def _build_search_text(extracted_data: Dict, rfp_content: str = None) -> str:
    """Build searchable text from extracted data and RFP content."""
    parts = []

    # Add extracted field values
    for key, value in extracted_data.items():
        if value and isinstance(value, str):
            parts.append(value)

    # Add RFP content if provided
    if rfp_content:
        parts.append(rfp_content)

    return " ".join(parts)


def _ai_assist_detection(extracted_data: Dict, rfp_content: str = None) -> Tuple[str, float, Dict]:
    """Use Claude to detect proposal type when keyword matching is inconclusive."""
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        search_text = _build_search_text(extracted_data, rfp_content)[:3000]  # Limit context

        response = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=200,
            messages=[
                {
                    "role": "user",
                    "content": f"""Analyze this RFP/security requirements document and identify the primary proposal type.

Available types:
- firewall_deployment: Network firewall, NGFW, zone-based security
- ot_asset_visibility: ICS/SCADA, industrial control, Modbus, OT/IT convergence
- soc: Security operations center, 24/7 monitoring, managed security
- siem: Log management, SIEM tools, correlation rules
- vulnerability_assessment: Penetration testing, vulnerability scanning
- managed_services: General MSSP services, outsourced security
- endpoint_security: EDR, XDR, endpoint protection
- cloud_security: CASB, CSPM, cloud posture management
- network_security: NAC, IDS/IPS, network segmentation
- compliance: Regulatory compliance, audit support

Return ONLY the type name (e.g., "firewall_deployment") as your response.

Content to analyze:
{search_text}"""
                }
            ]
        )

        detected_type = response.content[0].text.strip().lower().replace(" ", "_")

        # Validate the detected type is one of our known types
        if detected_type in PROPOSAL_TYPE_KEYWORDS:
            return detected_type, 0.75, {"source": "ai", "model": "claude"}
        else:
            return "managed_services", 0.6, {"source": "ai", "note": f"Detected '{detected_type}' not in known types"}

    except Exception as e:
        return "managed_services", 0.5, {"source": "ai_error", "error": str(e)}


def detect_industry_tags(extracted_data: Dict, rfp_content: str = None) -> List[str]:
    """Detect industry/environment tags from RFP content."""
    search_text = _build_search_text(extracted_data, rfp_content).lower()

    industry_keywords = {
        "ot": ["ot", "operational technology", "ics", "scada", "industrial", "manufacturing", "plant", "factory"],
        "ics": ["ics", "industrial control", "plc", "dcs", "control system"],
        "healthcare": ["hospital", "healthcare", "medical", "patient", "hipaa", "pharma"],
        "financial": ["bank", "financial", "trading", "payments", "pci dss", "fintech"],
        "government": ["government", "public sector", "gov", "defense", "military"],
        "retail": ["retail", "e-commerce", "pos", "point of sale"],
        "energy": ["energy", "utilities", "power", "oil", "gas", "renewable"],
        "telecom": ["telecom", "isp", "telecommunications", "network provider"]
    }

    detected = []
    for industry, keywords in industry_keywords.items():
        if any(kw in search_text for kw in keywords):
            detected.append(industry)

    return detected if detected else ["enterprise"]


def extract_additional_metadata(extracted_data: Dict, rfp_content: str = None) -> Dict:
    """Extract additional metadata from RFP like site count, architecture type, etc."""
    metadata = {
        "site_count": None,
        "architecture_type": None,
        "protocols": [],
        "vendors": [],
        "compliance_frameworks": [],
        "timeline_months": None
    }

    search_text = _build_search_text(extracted_data, rfp_content).lower()

    # Site count patterns
    site_patterns = [
        r'(\d+)\s*(?:site|location|facility|branch|office)',
        r'(\d+)\s*(?:plant|factory|warehouse)',
    ]
    for pattern in site_patterns:
        match = re.search(pattern, search_text)
        if match:
            metadata["site_count"] = int(match.group(1))
            break

    # Protocol detection
    protocol_keywords = {
        "modbus": "modbus",
        "profinet": "profinet",
        "ethernet/ip": "ethernet/ip",
        "dnp3": "dnp3",
        "bacnet": "bacnet",
        "honeywell": "honeywell",
        "siemens": "siemens",
        "rockwell": "rockwell",
        "schneider": "schneider"
    }
    for proto in protocol_keywords:
        if proto in search_text:
            metadata["protocols"].append(protocol_keywords[proto])

    # Architecture type
    if "distributed" in search_text:
        metadata["architecture_type"] = "distributed"
    elif "centralized" in search_text:
        metadata["architecture_type"] = "centralized"
    elif "hybrid" in search_text:
        metadata["architecture_type"] = "hybrid"
    elif "cloud" in search_text:
        metadata["architecture_type"] = "cloud"

    # Compliance frameworks
    compliance_patterns = [
        ("iso 27001", r'iso\s*27\s*0\s*0\s*1'),
        ("nist", r'nist\s*(?:800-53|cybersecurity framework|csf)?'),
        ("pci dss", r'pci\s*(?:dss|dss)'),
        ("hipaa", r'hipaa'),
        ("soc 2", r'soc\s*2'),
        ("gdpr", r'gdpr'),
    ]
    for name, pattern in compliance_patterns:
        if re.search(pattern, search_text):
            metadata["compliance_frameworks"].append(name)

    return metadata