"""
Role-Based Access Control (RBAC) Engine.
Enforces tool-level permissions based on UserRole (Admin vs Member).
"""

from models.user import UserRole

# Tools restricted to Administrator access (state mutations / critical actions)
ADMIN_ONLY_TOOLS = {
    "woo__create_product",
    "woo__update_order_status",
}


def is_tool_allowed_for_role(tool_name: str, role: UserRole) -> tuple[bool, str]:
    """
    Checks whether a user role has permission to execute a given tool.
    Returns:
        (is_allowed, error_reason)
    """
    if role == UserRole.ADMIN:
        return True, ""

    if tool_name in ADMIN_ONLY_TOOLS:
        return (
            False,
            f"Forbidden: User with role '{role.value}' is not permitted to execute administrative tool '{tool_name}'."
        )

    return True, ""
