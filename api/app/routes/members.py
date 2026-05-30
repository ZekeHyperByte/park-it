"""Member management routes (admin/operator)."""

from api.app.middleware.auth import require_admin
from api.app.models.member import Member
from api.app.routes.crud_factory import create_crud_router
from api.app.schemas.member import MemberCreate, MemberResponse, MemberUpdate
from shared.logging import get_logger

logger = get_logger("member_routes")

router = create_crud_router(
    model=Member,
    schema_create=MemberCreate,
    schema_update=MemberUpdate,
    schema_response=MemberResponse,
    prefix="/members",
    tags=["Members"],
    search_fields=["name", "card_number", "plate_number"],
    auth_dependency=require_admin,
    not_found_detail="Member not found",
)
