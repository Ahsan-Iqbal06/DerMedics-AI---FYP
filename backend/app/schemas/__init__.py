from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.core.security import password_problems


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Auth ----------
class RegisterIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(max_length=128)
    confirm_password: str
    country: str = Field(default="Pakistan", max_length=80)
    city: str = Field(default="", max_length=80)
    accept_terms: bool

    @field_validator("full_name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        v = " ".join(v.split())
        if len(v) < 2 or not any(c.isalpha() for c in v):
            raise ValueError("Enter your full name")
        return v

    @field_validator("email")
    @classmethod
    def lower_email(cls, v: str) -> str:
        return v.lower()

    @field_validator("password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        problems = password_problems(v)
        if problems:
            raise ValueError("Password must contain " + ", ".join(problems))
        return v

    @model_validator(mode="after")
    def check(self):
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        if not self.accept_terms:
            raise ValueError("You must accept the terms and privacy notice")
        return self


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshIn(BaseModel):
    refresh_token: str


class UserOut(ORM):
    id: int
    full_name: str
    email: str
    country: str
    city: str
    avatar_url: str | None = None
    created_at: datetime | None = None


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    country: str | None = Field(default=None, max_length=80)
    city: str | None = Field(default=None, max_length=80)


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(max_length=128)

    @field_validator("new_password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        problems = password_problems(v)
        if problems:
            raise ValueError("Password must contain " + ", ".join(problems))
        return v


class ForgotPasswordIn(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def lower_email(cls, v: str) -> str:
        return v.lower()


class VerifyResetCodeIn(ForgotPasswordIn):
    code: str = Field(pattern=r"^\d{6}$", description="6-digit code from the email")


class ResetTokenOut(BaseModel):
    reset_token: str
    expires_in: int = 600


class ResetPasswordIn(BaseModel):
    reset_token: str
    new_password: str = Field(max_length=128)
    confirm_password: str

    @field_validator("new_password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        problems = password_problems(v)
        if problems:
            raise ValueError("Password must contain " + ", ".join(problems))
        return v

    @model_validator(mode="after")
    def check(self):
        if self.new_password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class MessageOut(BaseModel):
    message: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


# ---------- AI pipeline ----------
class Prediction(BaseModel):
    label: str
    display_name: str
    confidence: float


class ConditionInfo(BaseModel):
    name: str
    overview: str
    symptoms: list[str] = []
    precautions: list[str] = []
    when_to_see_doctor: str = ""


class MedicineSuggestion(BaseModel):
    name: str
    type: str = ""  # e.g. "Topical", "Oral"
    usage_note: str = ""
    prescription_required: bool = False
    caution: str = ""


class DermatologistOut(ORM):
    id: int | None = None
    name: str
    kind: str = "doctor"
    clinic: str = ""
    qualification: str = ""
    country: str = ""
    city: str = ""
    address: str = ""
    phone: str = ""
    latitude: float | None = None
    longitude: float | None = None
    conditions: list[str] = []
    is_sample: bool = True
    source: str = "database"
    distance_km: float | None = None
    rating: float | None = None


class AnalysisOut(ORM):
    id: int
    status: Literal["ai", "inconclusive"]
    predicted_label: str | None
    display_name: str | None
    confidence: float
    top_predictions: list[Prediction] = []
    description: ConditionInfo | None = None
    medicines: list[MedicineSuggestion] = []
    region: str
    body_area: str
    symptoms: str
    is_demo: bool
    model_version: str
    llm_source: str
    image_url: str
    created_at: datetime | None = None
    dermatologists: list[DermatologistOut] = []
    has_report: bool = False


# ---------- Reports ----------
class ReportIn(BaseModel):
    analysis_id: int
    subject_type: Literal["myself", "someone_else"]
    subject_name: str | None = Field(default=None, max_length=120)
    subject_age: int | None = Field(default=None, ge=0, le=130)
    relationship: str | None = Field(default=None, max_length=40)
    health_notes: str = Field(default="", max_length=1000)

    @model_validator(mode="after")
    def check(self):
        if self.subject_type == "someone_else":
            if not self.subject_name or len(self.subject_name.strip()) < 2:
                raise ValueError("Enter the person's full name")
            if not self.relationship:
                raise ValueError("Select the relationship")
        return self


class ReportOut(BaseModel):
    id: int
    subject_type: str
    subject_name: str
    subject_age: int | None
    relationship: str
    health_notes: str
    created_at: datetime | None
    analysis: AnalysisOut


class ReportListItem(BaseModel):
    id: int
    analysis_id: int
    title: str
    subtitle: str
    status: str
    subject_name: str
    confidence: float
    created_at: datetime | None


class ActivityItem(BaseModel):
    kind: Literal["analysis", "report"]
    title: str
    ref_id: int
    created_at: datetime | None


class DashboardOut(BaseModel):
    analyses_count: int
    reports_count: int
    nearby_count: int
    recent_activity: list[ActivityItem]
