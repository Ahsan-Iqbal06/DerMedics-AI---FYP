from sqlalchemy import JSON, Boolean, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Dermatologist(Base):
    __tablename__ = "dermatologists"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(20), default="doctor")  # doctor | clinic
    clinic: Mapped[str] = mapped_column(String(160), default="")
    qualification: Mapped[str] = mapped_column(String(160), default="")
    country: Mapped[str] = mapped_column(String(80), index=True)
    city: Mapped[str] = mapped_column(String(80), index=True)
    address: Mapped[str] = mapped_column(String(255), default="")
    phone: Mapped[str] = mapped_column(String(40), default="")
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    # condition labels this provider commonly treats, e.g. ["acne", "eczema"]; empty = general dermatology
    conditions: Mapped[list] = mapped_column(JSON, default=list)
    is_sample: Mapped[bool] = mapped_column(Boolean, default=True)
