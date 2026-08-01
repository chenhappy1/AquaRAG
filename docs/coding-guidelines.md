# Coding Guidelines

## General Principles
- Keep the app modular and route-driven.
- Prefer standalone Angular components.
- Keep business logic in services where possible.
- Keep route-level components focused on UI and orchestration.
- Avoid mixing auth flow logic into the RAG UI component.

## Frontend Rules
- Use Angular signals for local component state.
- Use Reactive Forms for login and registration.
- Centralize HTTP auth behavior in interceptors and services.
- Keep route components simple and composable.

## Backend Rules
- Keep controllers thin.
- Put business logic into services.
- Use clear endpoint names and consistent JSON payloads.
- Respect user scoping for uploads and chat history.

## For AI and Automation
- When implementing a new feature, first review project context and architecture docs.
- Map the ticket to the relevant module before editing code.
- Prefer small, well-scoped changes over broad rewrites.
- Update docs when architecture or behavior changes.
