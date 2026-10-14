"""Policy illustrations. Production Django backend must enforce object-level ACLs."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Principal:
    user_id: str | None
    role: str  # public, member, contributor, editor, steward, admin
    steward_resource_ids: frozenset[str] = frozenset()


@dataclass(frozen=True)
class ContentObject:
    resource_id: str
    visibility: str  # public, restricted, private
    status: str  # draft, approved, archived
    owner_id: str | None = None
    sensitive: bool = False


def can_read(user: Principal, obj: ContentObject) -> bool:
    if obj.sensitive:
        return user.role == "admin"  # minimum illustration; not blanket production policy
    if obj.visibility == "public" and obj.status == "approved":
        return True
    if user.user_id is not None and user.user_id == obj.owner_id:
        return True
    return user.role in ("editor", "admin") and obj.visibility == "restricted"


def can_request_change(user: Principal, obj: ContentObject) -> bool:
    if user.user_id is None:
        return False
    return user.role in ("contributor", "editor", "steward", "admin")


def can_publish(user: Principal, obj: ContentObject) -> bool:
    if user.user_id is None or obj.sensitive:
        return False
    if user.role in ("editor", "admin"):
        return True
    if user.role == "steward" and obj.resource_id in user.steward_resource_ids:
        return True
    return False


def can_send_location(user: Principal, recipient_opted_in: bool,
                      current_explicit_approval: bool) -> bool:
    return bool(user.user_id and recipient_opted_in and current_explicit_approval)
