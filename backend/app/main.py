import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

import app.models  # noqa: F401  (register tables)
from app.api.routes import analysis, auth, care, reports
from app.core.config import get_settings
from app.db.session import Base, engine
from app.services.classifier import get_classifier
from app.services.llm import get_text_provider

logging.basicConfig(level=logging.INFO)


def create_app() -> FastAPI:
    s = get_settings()
    if s.auto_create_tables:
        Base.metadata.create_all(engine)
    s.upload_dir.mkdir(parents=True, exist_ok=True)

    app = FastAPI(title="DerMedics AI API", version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in s.cors_origins.split(",")],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        # Flatten pydantic errors into one readable message the app can show directly.
        messages = []
        for err in exc.errors():
            msg = str(err.get("msg", "Invalid value")).removeprefix("Value error, ")
            field = err.get("loc", [])[-1] if err.get("loc") else ""
            messages.append(msg if field in ("body", "") or msg[0].isupper() else f"{field}: {msg}")
        return JSONResponse(status_code=422, content={"detail": "; ".join(dict.fromkeys(messages))})

    for r in (auth.router, analysis.router, reports.router, care.router):
        app.include_router(r, prefix="/api")

    # Uploaded skin photos are served by random UUID name.
    app.mount("/uploads", StaticFiles(directory=s.upload_dir), name="uploads")

    @app.get("/api/health", tags=["meta"])
    def health():
        return {
            "status": "ok",
            "classifier": get_classifier().version,
            "text_provider": get_text_provider().source,
        }

    return app


app = create_app()
