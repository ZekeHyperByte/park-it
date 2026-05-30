"""Emoney reader management routes (admin only)."""

from api.app.middleware.auth import require_admin
from api.app.models.emoney_reader import EmoneyReader
from api.app.routes.crud_factory import create_crud_router
from api.app.schemas.emoney_reader import (
    EmoneyReaderCreate,
    EmoneyReaderResponse,
    EmoneyReaderUpdate,
)
from shared.logging import get_logger

logger = get_logger("emoney_reader_routes")

router = create_crud_router(
    model=EmoneyReader,
    schema_create=EmoneyReaderCreate,
    schema_update=EmoneyReaderUpdate,
    schema_response=EmoneyReaderResponse,
    prefix="/emoney-readers",
    tags=["E-Money Readers"],
    search_fields=["name", "code"],
    auth_dependency=require_admin,
    not_found_detail="E-money reader not found",
)
