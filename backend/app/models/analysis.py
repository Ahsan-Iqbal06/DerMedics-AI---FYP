from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    image_path: Mapped[str] = mapped_column(String(255))
    body_area: Mapped[str] = mapped_column(String(60), default="")
    symptoms: Mapped[str] = mapped_column(Text, default="")
    # "ai" when the model is confident enough, otherwise "inconclusive"
    status: Mapped[str] = mapped_column(String(20), index=True)
    predicted_label: Mapped[str | None] = mapped_column(String(80), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    top_predictions: Mapped[list] = mapped_column(JSON, default=list)
    description: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    medicines: Mapped[list] = mapped_column(JSON, default=list)
    region: Mapped[str] = mapped_column(String(80), default="")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    model_version: Mapped[str] = mapped_column(String(80), default="")
    llm_source: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="analyses")
    report = relationship("Report", back_populates="analysis", uselist=False, cascade="all, delete-orphan")


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), unique=True)
    # "myself" or "someone_else"
    subject_type: Mapped[str] = mapped_column(String(20))
    subject_name: Mapped[str] = mapped_column(String(120))
    subject_age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    relationship_to_user: Mapped[str] = mapped_column(String(40), default="Self")
    health_notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="reports")
    analysis = relationship("Analysis", back_populates="report")
