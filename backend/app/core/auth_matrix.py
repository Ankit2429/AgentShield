"""Authorization Matrix Engine for AgentShield.

Verifies agent capability mapping rules to prevent Tool Abuse,
Unauthorized Tool Calls, and Agent Identity Spoofing.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("agentshield.auth_matrix")


class AuthMatrix:
    """Agent and Service Capability Authorization Matrix."""

    def __init__(self) -> None:
        # Define roles for known agents to prevent Identity Spoofing
        self._agent_roles: dict[str, str] = {
            "agent-admin": "admin_agent",
            "agent-support": "support_agent",
            "agent-db": "database_agent",
            "agent-viewer": "viewer_agent",
            "agent-viewer-01": "viewer_agent",
            "agent-analyst-02": "support_agent",
            "agent-suspect-03": "viewer_agent",
            "agent-unknown-04": "viewer_agent",
        }

        # Define tool permission scopes per agent role
        self._role_permissions: dict[str, set[str]] = {
            "admin_agent": {"*"},
            "support_agent": {
                "fetch_user_details",
                "create_ticket",
                "read_faq",
                "list_services",
                "file_read",
            },
            "database_agent": {
                "read_database",
                "write_database",
                "db_query",
            },
            "viewer_agent": {
                "read_faq",
                "list_services",
            },
        }

    def verify_agent_identity(self, agent_id: str, claimed_role: str) -> bool:
        """Verify that the calling agent corresponds to their claimed role.

        Prevents Agent Identity Spoofing.
        """
        expected_role = self._agent_roles.get(agent_id)
        if not expected_role:
            logger.warning(f"[AUTH MATRIX] Identity spoofing check failed: unknown agent_id {agent_id!r}")
            return False

        is_valid = expected_role == claimed_role
        if not is_valid:
            logger.warning(
                f"[AUTH MATRIX] Identity spoofing detected: agent {agent_id!r} "
                f"claimed role {claimed_role!r} but matches {expected_role!r}"
            )
        return is_valid

    def check_authorization(self, agent_role: str, action: str, resource: str) -> bool:
        """Verify if an agent role is authorized to perform an action on a resource.

        Prevents Tool Abuse and Unauthorized Tool Calls.
        """
        allowed_actions = self._role_permissions.get(agent_role)
        if not allowed_actions:
            logger.warning(f"[AUTH MATRIX] Role {agent_role!r} has no registered permission scopes.")
            return False

        if "*" in allowed_actions:
            return True

        is_allowed = action in allowed_actions
        if not is_allowed:
            logger.warning(
                f"[AUTH MATRIX] Unauthorized tool call: role {agent_role!r} "
                f"attempted action {action!r} on resource {resource!r}"
            )
        return is_allowed


# Global singleton instance
auth_matrix = AuthMatrix()
