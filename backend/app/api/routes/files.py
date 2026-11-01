"""Uploaded photos, served only to their owner (skin photos are health data, so there is no public folder)."""

import re

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.models import Analysis, User

router = APIRouter(prefix="/files", tags=["files"])

# Stored names are always <uuid4 hex>.<ext>; anything else (e.g. "../") is rejected before touching the disk.
SAFE_NAME = re.compile(r"^[0-9a-f]{32}\.(jpg|png|webp)$")
NOT_FOUND = HTTPException(status.HTTP_404_NOT_FOUND, "File not found")


def _send(path) -> FileResponse:
    if not path.is_file():
        raise NOT_FOUND
    return FileResponse(path, headers={"Cache-Control": "private, max-age=3600"})


@router.get("/analyses/{name}")
def analysis_image(name: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not SAFE_NAME.match(name):
        raise NOT_FOUND
    owned = db.scalar(select(Analysis.id).where(Analysis.image_path == name, Analysis.user_id == user.id))
    if owned is None:
        raise NOT_FOUND
    return _send(get_settings().upload_dir / name)


@router.get("/avatars/{name}")
def avatar_image(name: str, user: User = Depends(get_current_user)):
    if not SAFE_NAME.match(name) or user.avatar_path != name:
        raise NOT_FOUND
    return _send(get_settings().upload_dir / "avatars" / name)
