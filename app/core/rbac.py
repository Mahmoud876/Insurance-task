from enum import StrEnum

from app.core.auth import AuthContext, Role


class Permission(StrEnum):
    CLAIM_READ = "claim:read"
    CLAIM_WRITE = "claim:write"
    CLAIM_CREATE = "claim:write"
    CLAIM_UPDATE = "claim:write"
    CLAIM_SCRUB = "claim:scrub"
    CLAIM_SUBMIT = "claim:write"
    CLAIM_DELETE = "claim:delete"


ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.ADMIN: {
        Permission.CLAIM_READ,
        Permission.CLAIM_WRITE,
        Permission.CLAIM_SCRUB,
        Permission.CLAIM_DELETE,
    },
    Role.BILLER: {
        Permission.CLAIM_READ,
        Permission.CLAIM_WRITE,
        Permission.CLAIM_SCRUB,
    },
    Role.AUDITOR: {
        Permission.CLAIM_READ,
    },
    Role.VIEWER: {
        Permission.CLAIM_READ,
    },
}


def check_permission(auth_ctx: AuthContext, required_permission: Permission) -> None:
    user_permissions = {
        perm for role in auth_ctx.roles for perm in ROLE_PERMISSIONS.get(role, set())
    }
    if required_permission not in user_permissions:
        raise PermissionError(f"Access denied. Required permission: '{required_permission}'")


__all__ = ["Role"]
