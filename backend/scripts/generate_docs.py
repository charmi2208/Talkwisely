"""
Regenerate the reference docs that are derived from code:

    docs/API.md       every endpoint, who may call it, and what it does
    docs/DATABASE.md  every table and column, from the SQLAlchemy models

Run from backend/ after changing routes or models:
    ./venv/bin/python scripts/generate_docs.py
"""

import inspect
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
DOCS = BACKEND.parent / "docs"
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("LOG_LEVEL", "WARNING")

from fastapi.routing import APIRoute  # noqa: E402

from app.api.v1 import (  # noqa: E402
    action_items, ai, analytics, auth, conversations, crm, integrations,
    knowledge_base, meetings, notifications, reports, sales, system, users,
)
from app.db.session import Base  # noqa: E402
import app.db.models  # noqa: E402,F401

API_PREFIX = "/api/v1"
MODULES = [
    ("Authentication", auth), ("Users & team", users), ("Conversations", conversations),
    ("Analytics", analytics), ("AI (Copilot, email, natural-language queries)", ai),
    ("Action items", action_items), ("Sales pipeline", sales), ("Meetings", meetings),
    ("CRM proposals", crm), ("Knowledge base", knowledge_base), ("Reports", reports),
    ("Integrations", integrations), ("Notifications", notifications), ("System & administration", system),
]
PUBLIC = {"/auth/register", "/auth/login", "/auth/refresh", "/auth/forgot-password", "/auth/reset-password"}


def _roles(route: APIRoute) -> str:
    """Roles required by a require_roles(...) dependency, if any."""
    stack = list(route.dependant.dependencies)
    while stack:
        dep = stack.pop()
        call = dep.call
        if getattr(call, "__name__", "") == "_check_roles" and call.__closure__:
            for cell in call.__closure__:
                if isinstance(cell.cell_contents, tuple):
                    return ", ".join(cell.cell_contents)
        stack.extend(dep.dependencies)
    return ""


def _summary(route: APIRoute) -> str:
    doc = inspect.getdoc(route.endpoint) or route.name.replace("_", " ")
    return doc.split("\n\n")[0].replace("\n", " ").replace("|", "\\|")


def api_markdown() -> str:
    lines = [
        "# API reference",
        "",
        "Generated from the FastAPI routes by `backend/scripts/generate_docs.py`; don't edit by hand.",
        "Interactive docs with request and response schemas: http://localhost:8000/api/docs",
        "",
        "All paths start with `/api/v1`. Every endpoint except the public auth ones needs",
        "`Authorization: Bearer <access token>` (from `POST /auth/login`).",
        "",
        "**Who can call it**",
        "- *Signed in*: any active user. Data is still limited to what the user may see: agents only get",
        "  conversations they uploaded (and anything derived from them); admins and managers see the whole",
        "  organization. Every query is scoped to the user's organization.",
        "- *admin*, *manager*: only those roles; others get 403.",
        "",
        "Errors use FastAPI's format: `{\"detail\": \"message\"}` (or a list of validation issues for 422).",
        "Rate limits: 10 requests per minute per IP on login, register and password reset; ",
        "`RATE_LIMIT_REQUESTS` per `RATE_LIMIT_PERIOD_SECONDS` on everything else (429 with `Retry-After`).",
        "",
    ]
    for title, module in MODULES:
        lines += [f"## {title}", "", "| Method | Path | Who | Description |", "|---|---|---|---|"]
        for route in module.router.routes:
            if not isinstance(route, APIRoute):
                continue
            path = route.path
            who = "Public" if path in PUBLIC else (_roles(route) or "Signed in")
            for method in sorted(route.methods - {"HEAD", "OPTIONS"}):
                lines.append(f"| {method} | `{path}` | {who} | {_summary(route)} |")
        lines.append("")
    lines += [
        "## Health",
        "",
        "| Method | Path | Who | Description |",
        "|---|---|---|---|",
        "| GET | `/health` (no `/api/v1` prefix) | Public | Service status and which AI providers are active |",
        "",
    ]
    return "\n".join(lines)


def database_markdown() -> str:
    lines = [
        "# Database schema",
        "",
        "Generated from the SQLAlchemy models (`backend/app/db/models/models.py`) by",
        "`backend/scripts/generate_docs.py`; don't edit by hand.",
        "",
        "- Primary keys are UUID strings (`VARCHAR(36)`).",
        "- Every organization-owned row carries `organization_id`, directly or through its conversation.",
        "- The schema is managed by Alembic (`backend/alembic/versions`). Run `python -m app.db.migrate`",
        "  (also run by `start.py`, the seed script and the Docker entrypoint) to create or upgrade it.",
        "- SQLite is used for local development and tests; PostgreSQL in Docker and production.",
        "",
        "## Entity overview",
        "",
        "```mermaid",
        "erDiagram",
    ]
    for table in Base.metadata.sorted_tables:
        for fk in table.foreign_keys:
            lines.append(f"    {fk.column.table.name} ||--o{{ {table.name} : \"{fk.parent.name}\"")
    lines += ["```", ""]

    for table in Base.metadata.sorted_tables:
        lines += [f"## `{table.name}`", "", "| Column | Type | Null | Notes |", "|---|---|---|---|"]
        for col in table.columns:
            notes = []
            if col.primary_key:
                notes.append("primary key")
            for fk in col.foreign_keys:
                notes.append(f"references `{fk.column.table.name}.{fk.column.name}`")
            if col.unique:
                notes.append("unique")
            lines.append(f"| `{col.name}` | {col.type} | {'yes' if col.nullable else 'no'} | {', '.join(notes)} |")
        indexes = sorted(ix.name for ix in table.indexes)
        if indexes:
            lines += ["", "Indexes: " + ", ".join(f"`{name}`" for name in indexes)]
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    (DOCS / "API.md").write_text(api_markdown())
    (DOCS / "DATABASE.md").write_text(database_markdown())
    print(f"Wrote {DOCS / 'API.md'} and {DOCS / 'DATABASE.md'}")
