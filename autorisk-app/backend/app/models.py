"""
SQLAlchemy models — one Python class per table in db/schema.sql.

Think of each class as a "shape" for a row: when SQLAlchemy reads a row
from the `policyholder` table, it hands you back a Policyholder object
whose attributes (.first_name, .email, ...) match the columns.
"""
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Date, DateTime, DECIMAL,
    ForeignKey, CheckConstraint, func
)
from sqlalchemy.orm import relationship
from .database import Base


class Region(Base):
    __tablename__ = "region"

    region_id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    region_type = Column(String(20), nullable=False)
    parent_region_id = Column(Integer, ForeignKey("region.region_id"))
    base_risk_factor = Column(DECIMAL(5, 2), nullable=False, default=1.00)

    children = relationship("Region")


class Policyholder(Base):
    __tablename__ = "policyholder"

    policyholder_id = Column(Integer, primary_key=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    license_number = Column(String(30), nullable=False, unique=True)
    license_issue_date = Column(Date, nullable=False)
    email = Column(String(100), nullable=False, unique=True)
    phone = Column(String(20))
    region_id = Column(Integer, ForeignKey("region.region_id"))
    risk_tier = Column(String(10))
    created_at = Column(DateTime, server_default=func.now())

    region = relationship("Region")
    vehicles = relationship("Vehicle", back_populates="policyholder")


class Vehicle(Base):
    __tablename__ = "vehicle"

    vehicle_id = Column(Integer, primary_key=True)
    policyholder_id = Column(Integer, ForeignKey("policyholder.policyholder_id"), nullable=False)
    make = Column(String(50), nullable=False)
    model = Column(String(50), nullable=False)
    manufacture_year = Column(Integer, nullable=False)
    engine_power_kw = Column(Integer, nullable=False)
    vin = Column(String(17), unique=True)
    usage_type = Column(String(20), nullable=False)

    policyholder = relationship("Policyholder", back_populates="vehicles")


class Coverage(Base):
    __tablename__ = "coverage"

    coverage_id = Column(Integer, primary_key=True)
    coverage_name = Column(String(50), nullable=False)
    description = Column(Text)
    is_mandatory = Column(Boolean, nullable=False, default=False)


class RateTable(Base):
    __tablename__ = "rate_table"

    rate_table_id = Column(Integer, primary_key=True)
    region_id = Column(Integer, ForeignKey("region.region_id"), nullable=False)
    coverage_id = Column(Integer, ForeignKey("coverage.coverage_id"), nullable=False)
    effective_date = Column(Date, nullable=False)
    expiry_date = Column(Date)
    base_rate = Column(DECIMAL(10, 2), nullable=False)
    age_factor_young = Column(DECIMAL(4, 2), nullable=False, default=1.00)
    age_factor_senior = Column(DECIMAL(4, 2), nullable=False, default=1.00)
    vehicle_power_factor = Column(DECIMAL(4, 2), nullable=False, default=1.00)
    bonus_malus_step = Column(DECIMAL(4, 2), nullable=False, default=1.00)


class Policy(Base):
    __tablename__ = "policy"

    policy_id = Column(Integer, primary_key=True)
    policyholder_id = Column(Integer, ForeignKey("policyholder.policyholder_id"), nullable=False)
    vehicle_id = Column(Integer, ForeignKey("vehicle.vehicle_id"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    status = Column(String(20), nullable=False, default="Pending")
    bonus_malus_coefficient = Column(DECIMAL(4, 2), nullable=False, default=1.00)
    total_premium = Column(DECIMAL(10, 2), nullable=False, default=0)
    created_at = Column(DateTime, server_default=func.now())

    policyholder = relationship("Policyholder")
    vehicle = relationship("Vehicle")
    coverages = relationship("PolicyCoverage", back_populates="policy")
    claims = relationship("Claim", back_populates="policy")


class PolicyCoverage(Base):
    __tablename__ = "policy_coverage"

    policy_id = Column(Integer, ForeignKey("policy.policy_id"), primary_key=True)
    coverage_id = Column(Integer, ForeignKey("coverage.coverage_id"), primary_key=True)
    coverage_limit = Column(DECIMAL(12, 2), nullable=False)
    deductible = Column(DECIMAL(10, 2), nullable=False, default=0)
    coverage_premium = Column(DECIMAL(10, 2), nullable=False, default=0)

    policy = relationship("Policy", back_populates="coverages")
    coverage = relationship("Coverage")


class Claim(Base):
    __tablename__ = "claim"

    claim_id = Column(Integer, primary_key=True)
    policy_id = Column(Integer, ForeignKey("policy.policy_id"), nullable=False)
    claim_date = Column(Date, nullable=False)
    claim_type = Column(String(30), nullable=False)
    description = Column(Text)
    status = Column(String(20), nullable=False, default="Open")
    fault_percentage = Column(DECIMAL(5, 2), nullable=False, default=0)
    reported_at = Column(DateTime, server_default=func.now())

    policy = relationship("Policy", back_populates="claims")
    payments = relationship("ClaimPayment", back_populates="claim")


class ClaimPayment(Base):
    __tablename__ = "claim_payment"

    claim_id = Column(Integer, ForeignKey("claim.claim_id"), primary_key=True)
    payment_seq = Column(Integer, primary_key=True)
    payment_date = Column(Date, nullable=False)
    amount = Column(DECIMAL(10, 2), nullable=False)
    payment_method = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default="Pending")

    claim = relationship("Claim", back_populates="payments")


class Account(Base):
    __tablename__ = "account"
    __table_args__ = (
        CheckConstraint(
            "account_type <> 'Customer' OR (policyholder_id IS NOT NULL AND admin_role IS NULL)",
            name="chk_customer_has_policyholder",
        ),
        CheckConstraint(
            "account_type <> 'Admin' OR (admin_role IS NOT NULL AND policyholder_id IS NULL)",
            name="chk_admin_has_role",
        ),
    )

    account_id = Column(Integer, primary_key=True)
    email = Column(String(100), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    account_type = Column(String(10), nullable=False)
    policyholder_id = Column(Integer, ForeignKey("policyholder.policyholder_id"))
    admin_role = Column(String(20))
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.now())
    last_login_at = Column(DateTime)

    policyholder = relationship("Policyholder")
