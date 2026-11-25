"""
Pydantic schemas — these define the *shape of JSON* that flows in and out
of the API. They're separate from the SQLAlchemy models in models.py on
purpose: models.py describes database rows, schemas.py describes the
request/response bodies React will send and receive. Pydantic validates
incoming JSON automatically (wrong type / missing field -> 422 error) and
FastAPI uses these classes to auto-generate the interactive docs at /docs.

Validation rules added after testing (see testing/docs/BUG_REPORTS.md):
every limit the DATABASE enforces (column lengths, CHECK constraints) is
also checked HERE, so bad input gets a clear 422 instead of crashing the
server with a 500 when Postgres rejects it.
"""
from datetime import date, datetime
from typing import Annotated, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator, model_validator

from . import clock


# Required strings: surrounding spaces stripped, not blank, and no longer
# than the database column (BUG-016).
Text30 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30)]
Text50 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]


def _not_in_future(value: date, what: str) -> date:
    if value > clock.today():
        raise ValueError(f"{what} cannot be in the future")
    return value


# ---------- Region ----------
class RegionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    region_id: int
    name: str
    region_type: str
    parent_region_id: Optional[int] = None
    base_risk_factor: float


# ---------- Policyholder ----------
class PolicyholderCreate(BaseModel):
    first_name: Text50
    last_name: Text50
    date_of_birth: date
    license_number: Text30
    license_issue_date: date
    email: Annotated[EmailStr, Field(max_length=100)]
    phone: Optional[Annotated[str, StringConstraints(strip_whitespace=True, max_length=20)]] = None
    region_id: Optional[int] = None
    risk_tier: Optional[Literal["Low", "Medium", "High"]] = None  # BUG-004: same values as the DB CHECK

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, v: str) -> str:
        return v.lower()  # BUG-015: emails are compared case-insensitively

    @field_validator("date_of_birth")
    @classmethod
    def dob_in_past(cls, v: date) -> date:
        return _not_in_future(v, "Date of birth")  # BUG-007

    @field_validator("license_issue_date")
    @classmethod
    def license_in_past(cls, v: date) -> date:
        return _not_in_future(v, "License issue date")

    @model_validator(mode="after")
    def license_after_birth(self):
        if self.license_issue_date <= self.date_of_birth:  # BUG-007
            raise ValueError("License issue date must be after the date of birth")
        return self


class PolicyholderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    policyholder_id: int
    first_name: str
    last_name: str
    date_of_birth: date
    license_number: str
    license_issue_date: date
    email: str
    phone: Optional[str] = None  # allows for null values in the phone field
    region_id: Optional[int] = None  # allows for null values in the region_id field
    risk_tier: Optional[str] = None # allows for null values in the risk_tier field
    created_at: datetime


# ---------- Vehicle ----------
class VehicleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    vehicle_id: int
    policyholder_id: int
    make: str
    model: str
    manufacture_year: int
    engine_power_kw: int
    vin: Optional[str] = None
    usage_type: str


# ---------- Coverage ----------
class CoverageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    coverage_id: int
    coverage_name: str
    description: Optional[str] = None
    is_mandatory: bool


# ---------- Claim / ClaimPayment ----------
class ClaimPaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    claim_id: int
    payment_seq: int
    payment_date: date
    amount: float
    payment_method: str
    status: str


class ClaimOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    claim_id: int
    policy_id: int
    claim_date: date
    claim_type: str
    description: Optional[str] = None
    status: str
    fault_percentage: float
    reported_at: datetime


class ClaimCreate(BaseModel):
    policy_id: int
    claim_date: date
    claim_type: Text30                                   # BUG-016: VARCHAR(30)
    description: Optional[str] = None
    fault_percentage: float = Field(0, ge=0, le=100)       # BUG-006: same range as the DB CHECK

    @field_validator("claim_date")
    @classmethod
    def claim_not_in_future(cls, v: date) -> date:
        return _not_in_future(v, "Claim date")             # BUG-008


# ---------- Policy ----------
class PolicyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    policy_id: int
    policyholder_id: int
    vehicle_id: int
    start_date: date
    end_date: date
    status: str
    bonus_malus_coefficient: float
    total_premium: float
    created_at: datetime


# ---------- Auth ----------
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, v: str) -> str:
        return v.lower()


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    account_id: int
    email: str
    account_type: str
    admin_role: Optional[str] = None


# ---------- Quote (pricing calculator) ----------
class QuoteRequest(BaseModel):
    # BUG-010: realistic ranges, so impossible inputs get a 422 instead of
    # a nonsense (even negative) premium.
    date_of_birth: date
    license_issue_date: date
    bonus_malus_coefficient: float = Field(ge=0.5, le=3.5)   # same range as the form
    vehicle_manufacture_year: int = Field(ge=1900)
    vehicle_power_kw: int = Field(ge=1, le=1000)
    region_id: int
    # Either one coverage_id, or full_coverage=true to bundle every coverage.
    coverage_id: Optional[int] = None
    full_coverage: bool = False

    @field_validator("date_of_birth")
    @classmethod
    def dob_in_past(cls, v: date) -> date:
        return _not_in_future(v, "Date of birth")

    @field_validator("license_issue_date")
    @classmethod
    def license_in_past(cls, v: date) -> date:
        return _not_in_future(v, "License issue date")

    @field_validator("vehicle_manufacture_year")
    @classmethod
    def year_not_in_future(cls, v: int) -> int:
        if v > clock.today().year + 1:  # next year's models are already on sale
            raise ValueError("Vehicle manufacture year is in the future")
        return v

    @model_validator(mode="after")
    def license_after_birth(self):
        if self.license_issue_date <= self.date_of_birth:
            raise ValueError("License issue date must be after the date of birth")
        return self

    @model_validator(mode="after")
    def coverage_chosen(self):
        if not self.full_coverage and self.coverage_id is None:
            raise ValueError("Choose a coverage or select Full Coverage")
        return self


class CoverageLine(BaseModel):
    """One coverage's share of a Full Coverage quote."""
    coverage_id: int
    coverage_name: str
    base_rate: float
    age_factor: float
    vehicle_power_factor: float
    estimated_premium: float


class QuoteResponse(BaseModel):
    estimated_premium: float          # for one policy term (see term_months)
    term_months: int = 6
    risk_level: str
    estimated_claim_frequency: float
    estimated_claim_severity: float
    pure_premium: float
    base_rate: float
    # None for Full Coverage: these differ per coverage (see coverage_breakdown)
    age_factor: Optional[float] = None
    experience_factor: float
    vehicle_power_factor: Optional[float] = None
    region_factor: float
    bonus_malus_adjustment: float
    # Full Coverage only
    full_coverage: bool = False
    subtotal_premium: Optional[float] = None
    discount_rate: Optional[float] = None
    discount_amount: Optional[float] = None
    coverage_breakdown: Optional[List[CoverageLine]] = None


class QuoteOption(BaseModel):
    """A region + coverage pair that has a current rate table (BUG-009).

    Regions where every coverage is priced also get a Full Coverage entry
    (coverage_id None, full_coverage True).
    """
    region_id: int
    region_name: str
    coverage_id: Optional[int] = None
    coverage_name: str
    full_coverage: bool = False


# ---------- Rate tables (admin) ----------
class RateTableOut(BaseModel):
    rate_table_id: int
    region_id: int
    region_name: str
    coverage_id: int
    coverage_name: str
    effective_date: date
    expiry_date: Optional[date] = None
    base_rate: float
    age_factor_young: float
    age_factor_senior: float
    vehicle_power_factor: float
    bonus_malus_step: float
    status: Literal["Current", "Scheduled", "Expired"]


class RateTableCreate(BaseModel):
    """A new rate VERSION. Existing rows are never edited: the version in
    force is closed (expiry_date = new effective_date) and this one starts."""
    region_id: int
    coverage_id: int
    effective_date: date
    base_rate: float = Field(gt=0, le=100000)
    age_factor_young: float = Field(1.0, ge=0.5, le=5)
    age_factor_senior: float = Field(1.0, ge=0.5, le=5)
    vehicle_power_factor: float = Field(1.0, ge=0.5, le=3)
    bonus_malus_step: float = Field(1.0, ge=0.5, le=3)

    @field_validator("effective_date")
    @classmethod
    def not_in_past(cls, v: date) -> date:
        # Backdating would re-price quotes already given for those days.
        if v < clock.today():
            raise ValueError("Effective date cannot be in the past")
        return v


# ---------- Accounts (admin) ----------
AdminRole = Literal["Analyst", "Administrator", "Manager"]
Password = Annotated[str, StringConstraints(min_length=8, max_length=128)]


class AccountOut(BaseModel):
    account_id: int
    email: str
    account_type: str
    admin_role: Optional[str] = None
    policyholder_id: Optional[int] = None
    policyholder_name: Optional[str] = None
    is_active: bool
    created_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None


class AccountCreate(BaseModel):
    email: Annotated[EmailStr, Field(max_length=100)]
    password: Password
    account_type: Literal["Customer", "Admin"]
    admin_role: Optional[AdminRole] = None
    policyholder_id: Optional[int] = None

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, v: str) -> str:
        return v.lower()

    @model_validator(mode="after")
    def matches_db_checks(self):
        # Same rules as chk_customer_has_policyholder / chk_admin_has_role
        if self.account_type == "Customer":
            if self.policyholder_id is None:
                raise ValueError("A customer account must be linked to a policyholder")
            if self.admin_role is not None:
                raise ValueError("A customer account cannot have a staff role")
        else:
            if self.admin_role is None:
                raise ValueError("A staff account needs a role")
            if self.policyholder_id is not None:
                raise ValueError("A staff account cannot be linked to a policyholder")
        return self


class AccountUpdate(BaseModel):
    is_active: Optional[bool] = None
    admin_role: Optional[AdminRole] = None


class PasswordReset(BaseModel):
    new_password: Password
