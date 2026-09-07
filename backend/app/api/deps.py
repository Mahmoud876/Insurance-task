from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database_session import SessionLocal
from app.core.security.auth import AuthContext
from app.core.security.rbac import ROLE_PERMISSIONS, Permission


def get_db(request: Request) -> Generator[Session, None, None]:
    request_db: Session | None = getattr(request.state, "db", None)
    if request_db is not None:
        yield request_db
        return

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_auth_context(request: Request) -> AuthContext:
    auth_ctx: AuthContext | None = getattr(request.state, "auth_context", None)
    if not auth_ctx or not isinstance(auth_ctx, AuthContext):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return auth_ctx


class PermissionChecker:
    required_permission: Permission | str

    def __init__(self, required_permission: Permission | str) -> None:
        if isinstance(required_permission, str):
            try:
                self.required_permission = Permission(required_permission)
            except ValueError:
                self.required_permission = required_permission
        else:
            self.required_permission = required_permission

    def __call__(
        self, auth_ctx: Annotated[AuthContext, Depends(get_current_auth_context)]
    ) -> AuthContext:
        roles = getattr(auth_ctx, "roles", []) or []
        user_permissions: set[Permission | str] = set()
        for role in roles:
            for perm in ROLE_PERMISSIONS.get(role, set()):
                user_permissions.add(perm)
                if hasattr(perm, "value"):
                    user_permissions.add(perm.value)

        target_perm = self.required_permission
        target_val = target_perm.value if isinstance(target_perm, Permission) else str(target_perm)

        if target_perm not in user_permissions and target_val not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{target_val}' required",
            )
        return auth_ctx


def require_permission(permission: Permission | str) -> PermissionChecker:
    return PermissionChecker(permission)
