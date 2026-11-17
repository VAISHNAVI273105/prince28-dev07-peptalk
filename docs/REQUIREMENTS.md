# PEPTalk - Project Requirements

## Functional Requirements

1. The system shall accept Python-related questions through a REST API.
2. The system shall provide answers using official Python PEP documents and What's New documentation.
3. The system shall identify the Python version associated with each feature.
4. The system shall provide source references for answers.
5. The system shall respond with exactly "I don't know" when a question is outside the supported documentation scope.

## Non-Functional Requirements

1. API endpoints shall respond within 2 seconds for local sample dataset requests.
2. The application shall start within 5 seconds in a local development environment.
3. The application shall have at least 6 passing automated tests.
4. Ruff linting shall complete with zero reported errors.
5. Every API response shall include a request ID, and application logs shall be structured JSON.
