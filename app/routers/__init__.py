from app.routers.auth import router as auth_router
from app.routers.monitors import public_router as public_monitors_router
from app.routers.monitors import router as monitors_router

__all__ = ["auth_router", "monitors_router", "public_monitors_router"]
