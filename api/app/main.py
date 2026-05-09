"""FastAPI application factory."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

from shared.config import get_settings
from shared.logging import configure_logging, get_logger

logger = get_logger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    configure_logging()
    logger.info("api_starting", app_name=app.title)

    settings = get_settings()
    logger.info(
        "api_config_loaded",
        env=settings.app_env,
        debug=settings.debug,
    )

    # Start WebSocket broadcaster
    from api.app.websocket.broadcaster import broadcaster
    await broadcaster.start()

    # Start event consumer (after broadcaster)
    from api.app.services.event_consumer import event_consumer
    await event_consumer.start()

    yield

    # Shutdown
    await event_consumer.stop()
    await broadcaster.stop()
    logger.info("api_shutting_down")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version="0.2.0",
        debug=settings.debug,
        lifespan=lifespan,
        docs_url="/api/docs" if settings.debug else None,
        redoc_url="/api/redoc" if settings.debug else None,
    )

    # Metrics middleware (before CORS so all requests are tracked)
    from api.app.middleware.metrics import get_metrics_response, metrics_middleware

    app.middleware("http")(metrics_middleware)

    # Metrics endpoint
    @app.get("/metrics")
    async def metrics() -> Response:
        return get_metrics_response()

    # Rate limiting
    from api.app.middleware.rate_limit import RateLimitMiddleware

    app.add_middleware(RateLimitMiddleware)

    # Security headers (defense in depth — also set at nginx layer)
    from api.app.middleware.security_headers import SecurityHeadersMiddleware

    app.add_middleware(SecurityHeadersMiddleware, enable_hsts=settings.app_env == "production")

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    from api.app.routes import (
        abandoned_vehicles,
        areas,
        audit_logs,
        auth,
        cameras,
        emoney_readers,
        gates_unified,
        health,
        manual_open_logs,
        member_groups,
        members,
        payments,
        pos,
        printers,
        reports,
        settlements,
        settings as settings_routes,
        shifts,
        site_config,
        snapshots,
        transactions,
        users,
        vehicle_types,
    )
    from api.app.websocket import handlers as ws_handlers

    app.include_router(health.router, prefix="/api")
    app.include_router(auth.router, prefix="/api")
    app.include_router(users.router, prefix="/api")
    app.include_router(gates_unified.router, prefix="/api")
    app.include_router(pos.router, prefix="/api")
    app.include_router(cameras.router, prefix="/api")
    app.include_router(settings_routes.router, prefix="/api")
    app.include_router(payments.router, prefix="/api")
    app.include_router(vehicle_types.router, prefix="/api")
    app.include_router(shifts.router, prefix="/api")
    app.include_router(areas.router, prefix="/api")
    app.include_router(emoney_readers.router, prefix="/api")
    app.include_router(members.router, prefix="/api")
    app.include_router(member_groups.router, prefix="/api")
    app.include_router(transactions.router, prefix="/api")
    app.include_router(manual_open_logs.router, prefix="/api")
    app.include_router(abandoned_vehicles.router, prefix="/api")
    app.include_router(reports.router, prefix="/api")
    app.include_router(site_config.router, prefix="/api")
    app.include_router(settlements.router, prefix="/api")
    app.include_router(audit_logs.router, prefix="/api")
    app.include_router(printers.router, prefix="/api")
    app.include_router(snapshots.router, prefix="/api")

    # WebSocket
    app.include_router(ws_handlers.router)

    return app


# Global app instance for uvicorn
app = create_app()
