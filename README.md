# PEPTalk

Your Python Documentation Assistant

PEPTalk helps Python developers find answers to modern Python questions using official Python Enhancement Proposals (PEPs) and Python's What's New documentation.

## Project Goal

Help developers understand Python version changes, newly introduced features, and their official documentation sources, especially when upgrading from Python 3.9 to Python 3.13.

## Tech Stack

- Python 3.12+
- FastAPI
- Pydantic Settings
- Uvicorn
- Pytest
- Ruff
- pre-commit

## Project Structure

PEPTalk/
    docs/
        QUESTIONS.md
        REQUIREMENTS.md
    src/
        peptalk/
    tests/
    data/
    pyproject.toml
    README.md

## Setup

    uv sync

## Run the Application

    uv run uvicorn peptalk.api.main:create_app --factory --reload --no-access-log

## Quality Checks

    uv run pytest
    uv run ruff check .

## Documentation Sources

- https://docs.python.org/3/
- https://peps.python.org/
- https://docs.python.org/3/whatsnew/

## Project

Prince 2028 - GenAI Engineer Program
DEV-07 | PEPTalk
