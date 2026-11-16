\set ON_ERROR_STOP on

BEGIN;

SELECT pg_advisory_xact_lock(hashtext('autorisk-fremtpl2-import'));


DO $$
BEGIN
    IF (SELECT count(*) FROM coverage WHERE coverage_name = 'Liability') <> 1 THEN
        RAISE EXCEPTION 'Expected exactly one team-seeded Liability coverage';
    END IF;
END $$;


CREATE TEMP TABLE import_region ON COMMIT DROP AS SELECT region_id, name, region_type, parent_region_id, base_risk_factor FROM region WITH NO DATA;

\copy import_region (region_id, name, region_type, parent_region_id, base_risk_factor) FROM 'region.csv' WITH (FORMAT csv, HEADER true)

INSERT INTO region (region_id, name, region_type, parent_region_id, base_risk_factor) SELECT region_id, name, region_type, parent_region_id, base_risk_factor FROM import_region ORDER BY region_id DESC ON CONFLICT DO NOTHING;

DO $$
BEGIN
    IF EXISTS (SELECT region_id, name, region_type, parent_region_id, base_risk_factor FROM import_region EXCEPT SELECT region_id, name, region_type, parent_region_id, base_risk_factor FROM region) THEN
        RAISE EXCEPTION 'Conflicting existing data in region';
    END IF;
END $$;

CREATE TEMP TABLE import_policyholder ON COMMIT DROP AS SELECT policyholder_id, first_name, last_name, date_of_birth, license_number, license_issue_date, email, region_id FROM policyholder WITH NO DATA;

\copy import_policyholder (policyholder_id, first_name, last_name, date_of_birth, license_number, license_issue_date, email, region_id) FROM 'policyholder.csv' WITH (FORMAT csv, HEADER true)

INSERT INTO policyholder (policyholder_id, first_name, last_name, date_of_birth, license_number, license_issue_date, email, region_id) SELECT policyholder_id, first_name, last_name, date_of_birth, license_number, license_issue_date, email, region_id FROM import_policyholder ON CONFLICT DO NOTHING;

DO $$
BEGIN
    IF EXISTS (SELECT policyholder_id, first_name, last_name, date_of_birth, license_number, license_issue_date, email, region_id FROM import_policyholder EXCEPT SELECT policyholder_id, first_name, last_name, date_of_birth, license_number, license_issue_date, email, region_id FROM policyholder) THEN
        RAISE EXCEPTION 'Conflicting existing data in policyholder';
    END IF;
END $$;

CREATE TEMP TABLE import_vehicle ON COMMIT DROP AS SELECT vehicle_id, policyholder_id, make, model, manufacture_year, engine_power_kw, usage_type FROM vehicle WITH NO DATA;

\copy import_vehicle (vehicle_id, policyholder_id, make, model, manufacture_year, engine_power_kw, usage_type) FROM 'vehicle.csv' WITH (FORMAT csv, HEADER true)

INSERT INTO vehicle (vehicle_id, policyholder_id, make, model, manufacture_year, engine_power_kw, usage_type) SELECT vehicle_id, policyholder_id, make, model, manufacture_year, engine_power_kw, usage_type FROM import_vehicle ON CONFLICT DO NOTHING;

DO $$
BEGIN
    IF EXISTS (SELECT vehicle_id, policyholder_id, make, model, manufacture_year, engine_power_kw, usage_type FROM import_vehicle EXCEPT SELECT vehicle_id, policyholder_id, make, model, manufacture_year, engine_power_kw, usage_type FROM vehicle) THEN
        RAISE EXCEPTION 'Conflicting existing data in vehicle';
    END IF;
END $$;

CREATE TEMP TABLE import_policy ON COMMIT DROP AS SELECT policy_id, policyholder_id, vehicle_id, start_date, end_date, status, bonus_malus_coefficient, total_premium FROM policy WITH NO DATA;

\copy import_policy (policy_id, policyholder_id, vehicle_id, start_date, end_date, status, bonus_malus_coefficient, total_premium) FROM 'policy.csv' WITH (FORMAT csv, HEADER true)

INSERT INTO policy (policy_id, policyholder_id, vehicle_id, start_date, end_date, status, bonus_malus_coefficient, total_premium) SELECT policy_id, policyholder_id, vehicle_id, start_date, end_date, status, bonus_malus_coefficient, total_premium FROM import_policy ON CONFLICT DO NOTHING;

DO $$
BEGIN
    IF EXISTS (SELECT policy_id, policyholder_id, vehicle_id, start_date, end_date, status, bonus_malus_coefficient, total_premium FROM import_policy EXCEPT SELECT policy_id, policyholder_id, vehicle_id, start_date, end_date, status, bonus_malus_coefficient, total_premium FROM policy) THEN
        RAISE EXCEPTION 'Conflicting existing data in policy';
    END IF;
END $$;

CREATE TEMP TABLE import_policy_coverage ON COMMIT DROP AS SELECT policy_id, coverage_limit, deductible, coverage_premium FROM policy_coverage WITH NO DATA;

\copy import_policy_coverage (policy_id, coverage_limit, deductible, coverage_premium) FROM 'policy_coverage.csv' WITH (FORMAT csv, HEADER true)

ALTER TABLE import_policy_coverage ADD COLUMN coverage_id integer;

UPDATE import_policy_coverage SET coverage_id = (SELECT coverage_id FROM coverage WHERE coverage_name = 'Liability');

INSERT INTO policy_coverage (policy_id, coverage_limit, deductible, coverage_premium, coverage_id) SELECT policy_id, coverage_limit, deductible, coverage_premium, coverage_id FROM import_policy_coverage ON CONFLICT DO NOTHING;

DO $$
BEGIN
    IF EXISTS (SELECT policy_id, coverage_limit, deductible, coverage_premium, coverage_id FROM import_policy_coverage EXCEPT SELECT policy_id, coverage_limit, deductible, coverage_premium, coverage_id FROM policy_coverage) THEN
        RAISE EXCEPTION 'Conflicting existing data in policy_coverage';
    END IF;
END $$;

CREATE TEMP TABLE import_claim ON COMMIT DROP AS SELECT claim_id, policy_id, claim_date, claim_type, status, reported_at FROM claim WITH NO DATA;

\copy import_claim (claim_id, policy_id, claim_date, claim_type, status, reported_at) FROM 'claim.csv' WITH (FORMAT csv, HEADER true)

INSERT INTO claim (claim_id, policy_id, claim_date, claim_type, status, reported_at) SELECT claim_id, policy_id, claim_date, claim_type, status, reported_at FROM import_claim ON CONFLICT DO NOTHING;

DO $$
BEGIN
    IF EXISTS (SELECT claim_id, policy_id, claim_date, claim_type, status, reported_at FROM import_claim EXCEPT SELECT claim_id, policy_id, claim_date, claim_type, status, reported_at FROM claim) THEN
        RAISE EXCEPTION 'Conflicting existing data in claim';
    END IF;
END $$;

CREATE TEMP TABLE import_claim_payment ON COMMIT DROP AS SELECT claim_id, payment_seq, payment_date, amount, payment_method, status FROM claim_payment WITH NO DATA;

\copy import_claim_payment (claim_id, payment_seq, payment_date, amount, payment_method, status) FROM 'claim_payment.csv' WITH (FORMAT csv, HEADER true)

INSERT INTO claim_payment (claim_id, payment_seq, payment_date, amount, payment_method, status) SELECT claim_id, payment_seq, payment_date, amount, payment_method, status FROM import_claim_payment ON CONFLICT DO NOTHING;

DO $$
BEGIN
    IF EXISTS (SELECT claim_id, payment_seq, payment_date, amount, payment_method, status FROM import_claim_payment EXCEPT SELECT claim_id, payment_seq, payment_date, amount, payment_method, status FROM claim_payment) THEN
        RAISE EXCEPTION 'Conflicting existing data in claim_payment';
    END IF;
END $$;

CREATE TEMP TABLE import_rate_table ON COMMIT DROP AS SELECT rate_table_id, region_id, effective_date, base_rate, age_factor_young, age_factor_senior, vehicle_power_factor, bonus_malus_step FROM rate_table WITH NO DATA;

\copy import_rate_table (rate_table_id, region_id, effective_date, base_rate, age_factor_young, age_factor_senior, vehicle_power_factor, bonus_malus_step) FROM 'rate_table.csv' WITH (FORMAT csv, HEADER true)

ALTER TABLE import_rate_table ADD COLUMN coverage_id integer;

UPDATE import_rate_table SET coverage_id = (SELECT coverage_id FROM coverage WHERE coverage_name = 'Liability');

INSERT INTO rate_table (rate_table_id, region_id, effective_date, base_rate, age_factor_young, age_factor_senior, vehicle_power_factor, bonus_malus_step, coverage_id) SELECT rate_table_id, region_id, effective_date, base_rate, age_factor_young, age_factor_senior, vehicle_power_factor, bonus_malus_step, coverage_id FROM import_rate_table ON CONFLICT DO NOTHING;

DO $$
BEGIN
    IF EXISTS (SELECT rate_table_id, region_id, effective_date, base_rate, age_factor_young, age_factor_senior, vehicle_power_factor, bonus_malus_step, coverage_id FROM import_rate_table EXCEPT SELECT rate_table_id, region_id, effective_date, base_rate, age_factor_young, age_factor_senior, vehicle_power_factor, bonus_malus_step, coverage_id FROM rate_table) THEN
        RAISE EXCEPTION 'Conflicting existing data in rate_table';
    END IF;
END $$;


SELECT (SELECT count(*) FROM import_policy) AS imported_policies,
       (SELECT count(*) FROM import_claim) AS imported_claims,
       (SELECT sum(amount) FROM import_claim_payment) AS imported_payment_total;
COMMIT;
