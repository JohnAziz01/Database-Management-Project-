"""
Pydantic schemas — these define the *shape of JSON* that flows in and out
of the API. They're separate from the SQLAlchemy models in models.py on
purpose: models.py describes database rows, schemas.py describes the
request/response bodies React will send and receive. Pydantic validates
incoming JSON automatically (wrong type / missing field -> 422 error) and
FastAPI uses these classes to auto-generate the interactive docs at /docs.
"""
from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, ConfigDict


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
    first_name: str
    last_name: str
    date_of_birth: date
    license_number: str
    license_issue_date: date
    email: EmailStr
    phone: Optional[str] = None
    region_id: Optional[int] = None
    risk_tier: Optional[str] = None


class PolicyholderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    policyholder_id: int
    first_name: str
    last_name: str
    date_of_birth: date
    license_number: str
    license_issue_date: date
    email: str
    phone: Optional[str] = None
    region_id: Optional[int] = None
    risk_tier: Optional[str] = None
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
    claim_type: str
    description: Optional[str] = None
    fault_percentage: float = 0


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


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    account_id: int
    email: str
    account_type: str


# ---------- Quote (pricing calculator) ----------
class QuoteRequest(BaseModel):
    date_of_birth: date
    license_issue_date: date
    bonus_malus_coefficient: float
    vehicle_manufacture_year: int
    vehicle_power_kw: int
    region_id: int
    coverage_id: int


class QuoteResponse(BaseModel):
    estimated_premium: float
    risk_level: str
    estimated_claim_frequency: float
    estimated_claim_severity: float
    pure_premium: float
    base_rate: float
    age_factor: float
    vehicle_power_factor: float
    region_factor: float
    bonus_malus_adjustment: float
