# ProposalCreator

AI-powered RFP analysis and proposal generation platform for cybersecurity consultants.

## Features

- **RFP Upload**: Upload RFPs in PDF, Word, or text format
- **AI Extraction**: Multiple extraction engines (Claude, OpenAI) extract key information
- **Data Editor**: Review and edit extracted data with confidence scores
- **Proposal Generation**: Generate Word documents from customizable templates
- **Template Management**: Create and manage proposal templates with placeholders

## Tech Stack

- **Backend**: Python + FastAPI
- **Frontend**: React + Next.js
- **Database**: PostgreSQL
- **AI**: Claude (Anthropic) + OpenAI

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Anthropic API key (for Claude)
- OpenAI API key (optional, for secondary extraction engine)

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd ProposalCreator
```

2. Copy the environment file:
```bash
cp .env.example .env
```

3. Edit `.env` and add your API keys:
```
ANTHROPIC_API_KEY=your_anthropic_api_key
OPENAI_API_KEY=your_openai_api_key
```

4. Start the application:
```bash
docker-compose up
```

5. Access the application:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Development Setup

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Database

The PostgreSQL database runs in Docker. To run migrations manually:

```bash
cd backend
alembic upgrade head
```

## Usage

### 1. Register/Login

Create an account or log in to access the platform.

### 2. Upload an RFP

Go to "Upload RFP" and either:
- Upload a PDF, Word, or text file
- Paste RFP content directly

### 3. Extract Data

Click "Extract Data" to run AI extraction. The system will:
- Extract key information using Claude (primary)
- Optionally use OpenAI for cross-validation
- Show confidence scores for each field

### 4. Review Extracted Data

Review and edit the extracted fields:
- Client information
- Scope of work
- Compliance requirements
- Timeline and deliverables
- Pricing information

### 5. Create a Proposal

Create a proposal from the extracted data and:
- Edit content as needed
- Preview the proposal
- Generate a Word document

### 6. Manage Templates

Create proposal templates with placeholders:
- Use `{{field_name}}` syntax for placeholders
- Example: `{{client_name}}`, `{{scope_of_work}}`
- Set a default template for auto-generation

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login
- `GET /api/auth/me` - Get current user

### RFPs
- `POST /api/rfps/upload` - Upload RFP
- `GET /api/rfps/` - List RFPs
- `GET /api/rfps/{id}` - Get RFP details
- `DELETE /api/rfps/{id}` - Delete RFP

### Extraction
- `POST /api/rfps/{id}/extract` - Extract data from RFP
- `GET /api/rfps/{id}/extraction-results` - Get extraction results

### Proposals
- `POST /api/proposals/` - Create proposal
- `GET /api/proposals/` - List proposals
- `GET /api/proposals/{id}` - Get proposal details
- `PUT /api/proposals/{id}` - Update proposal
- `POST /api/proposals/{id}/generate` - Generate Word document

### Templates
- `POST /api/templates/` - Create template
- `GET /api/templates/` - List templates
- `PUT /api/templates/{id}` - Update template
- `DELETE /api/templates/{id}` - Delete template

## Placeholders

Available placeholders for templates:

| Placeholder | Description |
|-------------|-------------|
| `{{client_name}}` | Client or company name |
| `{{project_title}}` | Project name |
| `{{scope_of_work}}` | Detailed scope |
| `{{requirements}}` | Requirements |
| `{{compliance_requirements}}` | Compliance standards |
| `{{security_requirements}}` | Security requirements |
| `{{pricing_information}}` | Pricing details |
| `{{contact_information}}` | Contact details |
| `{{deliverables}}` | Expected deliverables |
| `{{qualifications}}` | Qualifications |
| `{{timeline}}` | Project timeline |
| `{{terms_and_conditions}}` | Terms and conditions |

## Security

- JWT-based authentication
- Password hashing with bcrypt
- API keys stored in environment variables
- HTTPS recommended for production

## License

MIT License
