from fastapi import FastAPI
from oceantrace_common.config import settings

from oceantrace_api.routes import router


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="0.1.0")
    app.include_router(router, prefix="/api/v1")
    return app


app = create_app()

