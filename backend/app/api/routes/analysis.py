from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Analysis, User
from app.schemas import AnalysisOut
from app.services.classifier import InvalidImageError
from app.services.pipeline import run_analysis, to_out

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("", response_model=AnalysisOut, status_code=201)
async def analyze(
    image: UploadFile = File(...),
    body_area: str = Form(""),
    symptoms: str = Form("", max_length=1000),
    consent: bool = Form(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not consent:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Please confirm you understand this is not a medical diagnosis")
    data = await image.read()
    try:
        analysis = run_analysis(db, user, data, body_area.strip()[:60], symptoms.strip())
    except InvalidImageError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(e))
    return to_out(db, analysis, user)


@router.get("/{analysis_id}", response_model=AnalysisOut)
def get_analysis(analysis_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    analysis = db.get(Analysis, analysis_id)
    if analysis is None or analysis.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analysis not found")
    return to_out(db, analysis, user)
