"""
Role-based access helpers.

Roles (docs/SPEC.md §5):
- admin:   manages the organization, users, integrations and knowledge base; sees everything.
- manager: sees every conversation, team analytics and scorecards; generates reports.
- agent:   uploads conversations and sees only the conversations they uploaded
           ("assigned conversations") and their own performance.

``get_current_user`` loads ``user.user_roles`` eagerly, so these helpers never query.
"""

from app.db.models import Conversation

ROLE_PRIORITY = ("admin", "manager", "agent")
PRIVILEGED_ROLES = ("admin", "manager")


def role_names(user) -> set[str]:
    return {ur.role.name for ur in (user.user_roles or []) if ur.role}


def primary_role(user) -> str:
    """Highest-privilege role the user holds (admin > manager > agent)."""
    names = role_names(user)
    return next((r for r in ROLE_PRIORITY if r in names), "agent")


def is_privileged(user) -> bool:
    """Admins and managers see the whole organization."""
    return primary_role(user) in PRIVILEGED_ROLES


def conversation_scope(user) -> list:
    """WHERE conditions limiting Conversation rows to what ``user`` may see."""
    conditions = [Conversation.organization_id == user.organization_id]
    if not is_privileged(user):
        conditions.append(Conversation.created_by == user.id)
    return conditions
