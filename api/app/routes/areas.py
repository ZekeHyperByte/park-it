"""Area parkir management routes (admin only)."""

from api.app.middleware.auth import require_admin
from api.app.models.area_parkir import AreaParkir
from api.app.routes.crud_factory import create_crud_router
from api.app.schemas.area import AreaCreate, AreaResponse, AreaUpdate
from shared.logging import get_logger

logger = get_logger("area_routes")

router = create_crud_router(
    model=AreaParkir,
    schema_create=AreaCreate,
    schema_update=AreaUpdate,
    schema_response=AreaResponse,
    prefix="/areas",
    tags=["Areas"],
    search_fields=["name", "code"],
    auth_dependency=require_admin,
    not_found_detail="Area not found",
)
