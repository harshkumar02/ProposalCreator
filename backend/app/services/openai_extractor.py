from openai import OpenAI
from app.core.config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None


def extract_with_openai(content: str) -> list[dict]:
    if not settings.OPENAI_API_KEY:
        return []

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "system",
                "content": """You are an expert at analyzing RFPs (Requests for Proposals) for cybersecurity services. Extract structured information from the RFP document.

Extract these fields with confidence scores (0.0 to 1.0):
1. client_name - The organization issuing the RFP
2. project_title - Title or name of the project/service being sought
3. scope_of_work - Detailed description of the services required
4. timeline - Project timeline, milestones, or deadlines
5. compliance_requirements - Compliance standards (SOC2, ISO27001, NIST, etc.)
6. security_requirements - Specific security requirements
7. pricing_information - Budget or cost constraints
8. contact_information - Contact person details
9. deliverables - Expected deliverables
10. qualifications - Required qualifications or certifications
11. terms_and_conditions - Special terms or conditions

Return a JSON array with: field_name, value, confidence."""
            }, {
                "role": "user",
                "content": f"RFP CONTENT:\n{content}"
            }],
            response_format={"type": "json_object"},
        )

        import json
        response_text = response.choices[0].message.content

        try:
            data = json.loads(response_text)
            # Convert to the expected format
            if isinstance(data, dict) and "fields" in data:
                return data["fields"]
            elif isinstance(data, dict):
                results = []
                for key, value in data.items():
                    if isinstance(value, dict) and "value" in value:
                        results.append(value)
                    else:
                        results.append({
                            "field_name": key,
                            "value": str(value) if value else None,
                            "confidence": 0.7
                        })
                return results
        except json.JSONDecodeError:
            return []

    except Exception as e:
        print(f"OpenAI extraction error: {e}")
        return []


def extract_structured_data(content: str) -> list[dict]:
    """Extract structured data like dates, prices, quantities using regex patterns."""
    import re

    results = []

    # Extract dates
    date_patterns = [
        r'\b\d{1,2}/\d{1,2}/\d{4}\b',
        r'\b\d{4}-\d{2}-\d{2}\b',
        r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b',
    ]
    for pattern in date_patterns:
        dates = re.findall(pattern, content, re.IGNORECASE)
        if dates:
            results.append({
                "field_name": "dates_mentioned",
                "value": ", ".join(dates[:10]),
                "confidence": 0.8
            })
            break

    # Extract currency amounts
    currency_pattern = r'\$\s*[\d,]+(?:\.\d{2})?(?:\s*(?:k|K|million|M|B|budget|cost|price|fee)s?)?'
    amounts = re.findall(currency_pattern, content, re.IGNORECASE)
    if amounts:
        results.append({
            "field_name": "budget_mentioned",
            "value": ", ".join(set(amounts[:10])),
            "confidence": 0.7
        })

    # Extract email addresses
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, content)
    if emails:
        results.append({
            "field_name": "emails_mentioned",
            "value": ", ".join(set(emails[:5])),
            "confidence": 0.9
        })

    # Extract phone numbers
    phone_pattern = r'(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
    phones = re.findall(phone_pattern, content)
    if phones:
        results.append({
            "field_name": "phones_mentioned",
            "value": ", ".join(set(phones[:5])),
            "confidence": 0.8
        })

    return results