import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import app.models  # noqa: F401  (register tables)
from app.api.routes import analysis, auth, care, files, reports
from app.core.config import get_settings
from app.core.security import check_secret
from app.db.session import Base, engine
from app.services.classifier import get_classifier
from app.services.llm import get_text_provider

logging.basicConfig(level=logging.INFO)


def create_app() -> FastAPI:
    s = get_settings()
    check_secret()
    if s.auto_create_tables:
        Base.metadata.create_all(engine)
    s.upload_dir.mkdir(parents=True, exist_ok=True)

    app = FastAPI(title="DerMedics AI API", version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in s.cors_origins.split(",")],
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Error-Code"],
    )

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        if request.url.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")  # personal health data
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        # Flatten pydantic errors into one readable message the app can show directly.
        messages = []
        for err in exc.errors():
            msg = str(err.get("msg", "Invalid value")).removeprefix("Value error, ")
            field = err.get("loc", [])[-1] if err.get("loc") else ""
            messages.append(msg if field in ("body", "") or (msg and msg[0].isupper()) else f"{field}: {msg}")
        return JSONResponse(status_code=422, content={"detail": "; ".join(dict.fromkeys(messages))})

    # Uploaded photos are served by the owner-only /api/files routes, never as a public folder.
    for r in (auth.router, analysis.router, reports.router, care.router, files.router):
        app.include_router(r, prefix="/api")

    @app.get("/api/health", tags=["meta"])
    def health():
        return {
            "status": "ok",
            "classifier": get_classifier().version,
            "text_provider": get_text_provider().source,
        }

    return app


app = create_app()
