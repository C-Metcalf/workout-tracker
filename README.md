## Goal

Deliver a cross-platform PySide6 desktop app that tracks workouts, meals, and AI-assisted guidance with clean domain boundaries and reproducible workflows.

## Constraints

- Desktop UI built with PySide6/pyqtgraph already scaffolded; stay within SOLID/hexagonal guidelines.
- Local-first data storage (JSON/SQLite) with deterministic fixtures; no silent writes to restricted paths.
- Network access gated for AI calls—must run through configurable adapters/keys.
- Token/time budget favors incremental, testable slices; keep components <30 lines where feasible.

## Plan

1. **Domain & Storage (DONE)** – Added dataclasses and repository interfaces under `workout/domain`, plus JSON-backed repositories with schema versioning (`workout/storage/json_store.py`). Storage defaults to a portable JSON file with automatic backups and ID generation.  
2. **Services & Analytics** – Implement workout/meal services for CRUD, validation, macro/volume calculations, streak tracking, and expose observable DTOs for UI/AI contexts.  
3. **UI/Interactions** – Rework Qt tabs: logging forms, history tables with filtering, charts, meal planner, and AI chat dock; wire signals to services and keep widgets thin.  
4. **Visualization & Reporting** – Configure pyqtgraph dashboards for volume, PRs, calories, macros; enable date/attribute filtering and export to CSV/PDF.  
5. **AI Assistant** – Create adapter for preferred LLM (OpenAI/local) with prompt templates pulling recent workout/meal summaries; handle auth via env vars and show conversation history.  
6. **Testing & Tooling** – Add pytest suite for domain/services, Qt smoke tests, linting (ruff/black), and GitHub Actions (format, tests); seed sample data like `11-2025.json`.

## Risks & Mitigations

- **Data integrity** – Introduce schema versioning and validation before writes; add backups/export commands.  
- **UI complexity** – Separate widgets per feature and rely on presenter/view-model classes to keep logic testable.  
- **AI latency/cost** – Cache recent responses, allow model selection, include clear error handling & rate limiting.

## Deliverables

- Domain models & repository adapters with docs/tests.  
- Service layer for workouts/meals/insights plus pyqtgraph dashboards.  
- PySide6 UI components for logging, analytics, and chat.  
- AI adapter module with configurable providers.  
- Automated tests, lint config, and usage docs (README + inline help).
