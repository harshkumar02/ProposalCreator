import anthropic
from app.core.config import settings

client = anthropic.Anthropic()


def extract_with_claude(content: str) -> list[dict]:
    if not settings.ANTHROPIC_API_KEY:
        return []

    try:
        message = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": f"""You are an expert at analyzing RFPs (Requests for Proposals) for cybersecurity services, specifically for MSSP proposals from 63SATS.

Extract structured information from the following RFP document for a comprehensive cybersecurity proposal.

Extract the following fields with confidence scores (0.0 to 1.0):

1. client_name - The organization issuing the RFP
2. project_title - Title or name of the project/service being sought
3. current_challenges - Current security challenges or problems mentioned by the client
4. objectives - Project objectives and goals
5. assets - IT assets, systems, and infrastructure in scope
6. key_services - Specific services being requested
7. solution_proposed - Any preferred solution or approach mentioned
8. implementation_approach - Desired implementation approach or methodology
9. implementation_methodology - Specific methodology or framework preferences
10. timeline - Project timeline, milestones, or deadlines
11. assumptions - Any assumptions mentioned in the RFP
12. expected_outcomes - Expected results or ROI mentioned
13. contact_information - Contact person details
14. compliance_requirements - Compliance standards mentioned (SOC2, ISO27001, NIST, etc.)
15. security_requirements - Specific security requirements
16. pricing_information - Budget, pricing structure, or cost constraints
17. qualifications - Required qualifications or certifications
18. deliverables - Expected deliverables or outcomes
19. terms_and_conditions - Any special terms or conditions

Return your response as a JSON array with objects containing:
- field_name: the field identifier (use snake_case like the examples above)
- value: the extracted value (or null if not found)
- confidence: a number between 0 and 1

IMPORTANT: Map the extracted information to the most appropriate field. If a section is not explicitly mentioned in the RFP, provide a reasonable placeholder that can be customized later.

RFP CONTENT:
{content}

Return ONLY the JSON array, no explanation."""
            }]
        )

        import json
        response_text = message.content[0].text

        # Try to parse as JSON array
        try:
            results = json.loads(response_text)
            return results
        except json.JSONDecodeError:
            # Try to extract JSON from the response
            import re
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                results = json.loads(json_match.group(0))
                return results
            return []

    except Exception as e:
        print(f"Claude extraction error: {e}")
        return []


def summarize_with_claude(content: str, max_length: int = 2000) -> str:
    if not settings.ANTHROPIC_API_KEY:
        return content[:max_length]

    try:
        message = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": f"""Summarize the following RFP document in a concise manner for a cybersecurity MSSP proposal. Focus on:
- Key requirements
- Important deadlines
- Critical compliance needs
- Scope of work
- Client challenges mentioned

Keep the summary under 500 words.

CONTENT:
{content[:10000]}"""
            }]
        )
        return message.content[0].text
    except Exception as e:
        print(f"Claude summarization error: {e}")
        return content[:max_length]