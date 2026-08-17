from fastapi import Depends, HTTPException



ROLE_PERMISSIONS = {
    "employee": {
        "ticket:read",
    },
    "manager": {
        "ticket:read",
        "ticket:create",
        "ticket:assign",
        "ticket:update_status",
    },
    "admin": {
        "ticket:read",
        "ticket:create",
        "ticket:assign",
        "ticket:update_status",
        "ticket:delete",
        "user:manage",
    },
}

def require_permission(permission: str, get_current_user):
    def permission_checker(
        current_user: dict= Depends(get_current_user)
    ):
        role= current_user.get("role")

        permissions= ROLE_PERMISSIONS.get(role, set())

        if permission not in permissions:
            raise HTTPException(
                status_code= 403,
                detail= f"Permission required: {permission}"
            )
        return current_user
    return permission_checker

def require_same_department(
    department: str,
    current_user: dict
):
    if current_user.get("role") == "admin":
        return current_user

    if current_user.get("department") != department:
        raise HTTPException(
            status_code=403,
            detail="Access restricted to your department"
        )

    return current_user

def can_access_ticket(current_user: dict, ticket):
    role= current_user.get("role")

    if role =='admin':
        return True

    if role =="manager":
        return current_user.get("department") == ticket.department

    if role == "employee":
        return current_user.get("sub") == ticket.owner.username

    return False