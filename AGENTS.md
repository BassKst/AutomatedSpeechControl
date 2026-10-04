# Project Instructions

## Project

AutomatedSpeechControl is a Python application for voice-controlled
assistant functionality.

The project contains:
- speech recognition;
- text-to-speech;
- NLU;
- voice biometrics;
- database persistence;
- Telegram/local audio channels;
- deployment automation;
- Terraform/Ansible infrastructure.

## General rules

1. Do not perform large-scale rewrites without explicit approval.
2. Prefer small, isolated changes.
3. Preserve existing behavior unless a change is explicitly requested.
4. Before modifying architecture, explain the proposed change.
5. Do not expose or commit secrets.
6. Never modify production credentials.
7. Never delete functionality just to simplify the code.
8. Run relevant tests after modifications.
9. Run static analysis/linting when appropriate.
10. Keep changes reviewable and logically grouped.

## Python

- Follow modern Python practices.
- Prefer type hints.
- Avoid unnecessary abstractions.
- Keep modules focused.
- Handle exceptions explicitly.
- Avoid global mutable state where possible.

## Architecture

Before introducing a new abstraction, check whether an existing
abstraction already solves the problem.

Do not introduce frameworks or dependencies without justification.

## Database

Database schema changes must use Alembic migrations.

Never modify the database schema manually without creating
the corresponding migration.

## Security

Treat:
- .env
- API keys
- encryption keys
- private certificates
- database credentials
- tokens

as secrets.

Never commit them.

## Git

Make small, focused commits.

Do not mix:
- refactoring;
- bug fixes;
- formatting;
- dependency upgrades

in one commit unless explicitly requested.