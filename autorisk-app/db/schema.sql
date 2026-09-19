-- AutoRisk: Car Insurance Pricing & Risk Analytics
-- PostgreSQL schema generated from car_insurance_erd.drawio
-- Run with: psql -U postgres -d autorisk -f db/schema.sql

-- Clean slate (safe to re-run while developing)
DROP TABLE IF EXISTS claim_payment CASCADE;
DROP TABLE IF EXISTS claim CASCADE;
DROP TABLE IF EXISTS policy_coverage CASCADE;
DROP TABLE IF EXISTS policy CASCADE;
DROP TABLE IF EXISTS rate_table CASCADE;
DROP TABLE IF EXISTS account CASCADE;
DROP TABLE IF EXISTS vehicle CASCADE;
DROP TABLE IF EXISTS policyholder CASCADE;
DROP TABLE IF EXISTS coverage CASCADE;
DROP TABLE IF EXISTS region CASCADE;

-- ─────────────────────────────────────────────────────────
-- REGION — self-referencing hierarchy (country > state > district)
-- ─────────────────────────────────────────────────────────
CREATE TABLE region (
    region_id         SERIAL PRIMARY KEY,
    name              VARCHAR(100) NOT NULL,
    region_type       VARCHAR(20)  NOT NULL,          -- e.g. Country / State / District
    parent_region_id  INTEGER REFERENCES region(region_id),
    base_risk_factor  DECIMAL(5,2) NOT NULL DEFAULT 1.00
);

-- ─────────────────────────────────────────────────────────
-- POLICYHOLDER
-- ─────────────────────────────────────────────────────────
CREATE TABLE policyholder (
    policyholder_id     SERIAL PRIMARY KEY,
    first_name          VARCHAR(50)  NOT NULL,
    last_name           VARCHAR(50)  NOT NULL,
    date_of_birth       DATE         NOT NULL,
    license_number      VARCHAR(30)  NOT NULL UNIQUE,
    license_issue_date  DATE         NOT NULL,
    email               VARCHAR(100) NOT NULL UNIQUE,
    phone               VARCHAR(20),
    region_id           INTEGER REFERENCES region(region_id),
    risk_tier           VARCHAR(10) CHECK (risk_tier IN ('Low','Medium','High')),
    created_at          TIMESTAMP NOT NULL DEFAULT now()
);

-- ─────────────────────────────────────────────────────────
-- VEHICLE
-- ─────────────────────────────────────────────────────────
CREATE TABLE vehicle (
    vehicle_id         SERIAL PRIMARY KEY,
    policyholder_id     INTEGER NOT NULL REFERENCES policyholder(policyholder_id),
    make                VARCHAR(50) NOT NULL,
    model               VARCHAR(50) NOT NULL,
    manufacture_year    INTEGER NOT NULL,
    engine_power_kw     INTEGER NOT NULL,
    vin                 VARCHAR(17) UNIQUE,
    usage_type          VARCHAR(20) NOT NULL CHECK (usage_type IN ('Personal','Business','Commercial','Other'))
);

-- ─────────────────────────────────────────────────────────
-- COVERAGE — catalog of coverage types (Liability, Collision, ...)
-- ─────────────────────────────────────────────────────────
CREATE TABLE coverage (
    coverage_id     SERIAL PRIMARY KEY,
    coverage_name   VARCHAR(50) NOT NULL,
    description     TEXT,
    is_mandatory    BOOLEAN NOT NULL DEFAULT false
);

-- ─────────────────────────────────────────────────────────
-- RATE_TABLE — versioned pricing factors per Region + Coverage
-- ─────────────────────────────────────────────────────────
CREATE TABLE rate_table (
    rate_table_id         SERIAL PRIMARY KEY,
    region_id             INTEGER NOT NULL REFERENCES region(region_id),
    coverage_id           INTEGER NOT NULL REFERENCES coverage(coverage_id),
    effective_date        DATE NOT NULL,
    expiry_date           DATE,                       -- NULL = still current
    base_rate             DECIMAL(10,2) NOT NULL,
    age_factor_young       DECIMAL(4,2) NOT NULL DEFAULT 1.00,
    age_factor_senior      DECIMAL(4,2) NOT NULL DEFAULT 1.00,
    vehicle_power_factor   DECIMAL(4,2) NOT NULL DEFAULT 1.00,
    bonus_malus_step       DECIMAL(4,2) NOT NULL DEFAULT 1.00,
    CHECK (expiry_date IS NULL OR expiry_date > effective_date)
);

-- ─────────────────────────────────────────────────────────
-- POLICY
-- ─────────────────────────────────────────────────────────
CREATE TABLE policy (
    policy_id                 SERIAL PRIMARY KEY,
    policyholder_id           INTEGER NOT NULL REFERENCES policyholder(policyholder_id),
    vehicle_id                INTEGER NOT NULL REFERENCES vehicle(vehicle_id),
    start_date                DATE NOT NULL,
    end_date                  DATE NOT NULL,
    status                    VARCHAR(20) NOT NULL DEFAULT 'Pending'
                               CHECK (status IN ('Active','Pending','Expired')),
    bonus_malus_coefficient   DECIMAL(4,2) NOT NULL DEFAULT 1.00,
    total_premium             DECIMAL(10,2) NOT NULL DEFAULT 0,
    created_at                TIMESTAMP NOT NULL DEFAULT now(),
    CHECK (end_date > start_date)
);

-- ─────────────────────────────────────────────────────────
-- POLICY_COVERAGE — associative entity (many-to-many Policy <-> Coverage)
-- ─────────────────────────────────────────────────────────
CREATE TABLE policy_coverage (
    policy_id          INTEGER NOT NULL REFERENCES policy(policy_id),
    coverage_id        INTEGER NOT NULL REFERENCES coverage(coverage_id),
    coverage_limit      DECIMAL(12,2) NOT NULL,
    deductible          DECIMAL(10,2) NOT NULL DEFAULT 0,
    coverage_premium    DECIMAL(10,2) NOT NULL DEFAULT 0,
    PRIMARY KEY (policy_id, coverage_id)
);

-- ─────────────────────────────────────────────────────────
-- CLAIM
-- ─────────────────────────────────────────────────────────
CREATE TABLE claim (
    claim_id         SERIAL PRIMARY KEY,
    policy_id        INTEGER NOT NULL REFERENCES policy(policy_id),
    claim_date       DATE NOT NULL,
    claim_type       VARCHAR(30) NOT NULL,
    description      TEXT,
    status           VARCHAR(20) NOT NULL DEFAULT 'Open'
                       CHECK (status IN ('Open','Pending','Paid','Denied')),
    fault_percentage DECIMAL(5,2) NOT NULL DEFAULT 0 CHECK (fault_percentage BETWEEN 0 AND 100),
    reported_at      TIMESTAMP NOT NULL DEFAULT now()
);

-- ─────────────────────────────────────────────────────────
-- CLAIM_PAYMENT — weak entity: identified by (claim_id, payment_seq)
-- ─────────────────────────────────────────────────────────
CREATE TABLE claim_payment (
    claim_id        INTEGER NOT NULL REFERENCES claim(claim_id),
    payment_seq     INTEGER NOT NULL,
    payment_date    DATE NOT NULL,
    amount          DECIMAL(10,2) NOT NULL,
    payment_method  VARCHAR(20) NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'Pending',
    PRIMARY KEY (claim_id, payment_seq)
);

-- ─────────────────────────────────────────────────────────
-- ACCOUNT — login accounts; either linked to a policyholder (customer)
-- or carries an admin_role (staff). Exactly one of the two per CHECKs.
-- ─────────────────────────────────────────────────────────
CREATE TABLE account (
    account_id       SERIAL PRIMARY KEY,
    email            VARCHAR(100) NOT NULL UNIQUE,
    password_hash    VARCHAR(255) NOT NULL,
    account_type     VARCHAR(10) NOT NULL CHECK (account_type IN ('Customer','Admin')),
    policyholder_id  INTEGER REFERENCES policyholder(policyholder_id),
    admin_role       VARCHAR(20) CHECK (admin_role IN ('Analyst','Administrator','Manager')),
    is_active        BOOLEAN NOT NULL DEFAULT true,
    created_at       TIMESTAMP NOT NULL DEFAULT now(),
    last_login_at    TIMESTAMP,
    CONSTRAINT chk_customer_has_policyholder
        CHECK (account_type <> 'Customer' OR (policyholder_id IS NOT NULL AND admin_role IS NULL)),
    CONSTRAINT chk_admin_has_role
        CHECK (account_type <> 'Admin' OR (admin_role IS NOT NULL AND policyholder_id IS NULL))
);

-- Helpful indexes for the lookups the UI does constantly
CREATE INDEX idx_policy_policyholder ON policy(policyholder_id);
CREATE INDEX idx_policy_vehicle ON policy(vehicle_id);
CREATE INDEX idx_vehicle_policyholder ON vehicle(policyholder_id);
CREATE INDEX idx_claim_policy ON claim(policy_id);
CREATE INDEX idx_rate_table_region_coverage ON rate_table(region_id, coverage_id);
CREATE INDEX idx_policyholder_region ON policyholder(region_id);
