-- Small seed dataset so the app isn't empty on first run.
-- Run after schema.sql: psql -U postgres -d autorisk -f db/seed.sql

INSERT INTO region (name, region_type, parent_region_id, base_risk_factor) VALUES
    ('National', 'Country', NULL, 1.00);
INSERT INTO region (name, region_type, parent_region_id, base_risk_factor) VALUES
    ('Region A', 'State', 1, 1.10),
    ('Region B', 'State', 1, 0.95),
    ('Region C', 'State', 1, 1.25);

INSERT INTO coverage (coverage_name, description, is_mandatory) VALUES
    ('Liability', 'Covers damage/injury you cause to others', true),
    ('Collision', 'Covers damage to your own vehicle from a collision', false),
    ('Comprehensive', 'Covers theft, weather, and other non-collision damage', false),
    ('Uninsured Motorist', 'Covers you if the other driver has no insurance', false);

INSERT INTO rate_table (region_id, coverage_id, effective_date, base_rate, age_factor_young, age_factor_senior, vehicle_power_factor, bonus_malus_step) VALUES
    (2, 1, '2026-01-01', 450.00, 1.60, 1.10, 1.05, 1.00),
    (3, 1, '2026-01-01', 380.00, 1.50, 1.05, 1.04, 1.00),
    (4, 1, '2026-01-01', 520.00, 1.75, 1.15, 1.08, 1.00);

-- BUG-009 fix: rate tables for the other coverages, so every coverage the
-- Quote form offers in Regions A/B/C can actually be priced.
-- (coverage 2 = Collision, 3 = Comprehensive, 4 = Uninsured Motorist)
INSERT INTO rate_table (region_id, coverage_id, effective_date, base_rate, age_factor_young, age_factor_senior, vehicle_power_factor, bonus_malus_step) VALUES
    (2, 2, '2026-01-01', 320.00, 1.55, 1.10, 1.06, 1.00),
    (2, 3, '2026-01-01', 180.00, 1.20, 1.05, 1.03, 1.00),
    (2, 4, '2026-01-01',  90.00, 1.30, 1.05, 1.00, 1.00),
    (3, 2, '2026-01-01', 280.00, 1.45, 1.05, 1.05, 1.00),
    (3, 3, '2026-01-01', 150.00, 1.15, 1.05, 1.02, 1.00),
    (3, 4, '2026-01-01',  75.00, 1.25, 1.05, 1.00, 1.00),
    (4, 2, '2026-01-01', 360.00, 1.70, 1.15, 1.07, 1.00),
    (4, 3, '2026-01-01', 210.00, 1.25, 1.10, 1.04, 1.00),
    (4, 4, '2026-01-01', 105.00, 1.35, 1.10, 1.00, 1.00);

INSERT INTO policyholder (first_name, last_name, date_of_birth, license_number, license_issue_date, email, phone, region_id, risk_tier) VALUES
    ('Jordan', 'Reyes', '1990-04-12', 'D1234567', '2009-05-01', 'jordan.reyes@example.com', '555-0101', 2, 'Low'),
    ('Casey', 'Nguyen', '2002-11-03', 'D7654321', '2020-11-20', 'casey.nguyen@example.com', '555-0102', 3, 'Medium'),
    ('Priya', 'Shah', '1975-02-17', 'D9988776', '1994-03-10', 'priya.shah@example.com', '555-0103', 4, 'Low');

INSERT INTO vehicle (policyholder_id, make, model, manufacture_year, engine_power_kw, vin, usage_type) VALUES
    (1, 'Toyota', 'Camry', 2022, 138, '1HGCM82633A004352', 'Personal'),
    (2, 'Honda', 'Civic', 2019, 104, '2HGES16575H542891', 'Personal'),
    (3, 'Ford', 'F-150', 2021, 250, '1FTFW1E5XMFA00001', 'Business');

INSERT INTO policy (policyholder_id, vehicle_id, start_date, end_date, status, bonus_malus_coefficient, total_premium) VALUES
    (1, 1, '2026-01-01', '2027-01-01', 'Active', 0.90, 610.50),
    (2, 2, '2026-03-01', '2027-03-01', 'Active', 1.15, 705.00),
    (3, 3, '2025-09-01', '2026-09-01', 'Expired', 1.00, 890.25);

INSERT INTO policy_coverage (policy_id, coverage_id, coverage_limit, deductible, coverage_premium) VALUES
    (1, 1, 100000.00, 500.00, 480.00),
    (1, 2, 50000.00, 1000.00, 130.50),
    (2, 1, 100000.00, 500.00, 705.00),
    (3, 1, 150000.00, 250.00, 890.25);

INSERT INTO claim (policy_id, claim_date, claim_type, description, status, fault_percentage) VALUES
    (1, '2026-05-14', 'Collision', 'Rear-ended at a stoplight', 'Paid', 0.00),
    (2, '2026-06-02', 'Theft', 'Vehicle stolen from parking lot', 'Pending', 0.00);

INSERT INTO claim_payment (claim_id, payment_seq, payment_date, amount, payment_method, status) VALUES
    (1, 1, '2026-05-28', 2400.00, 'Direct Deposit', 'Paid');

-- Password for admin@autorisk.demo   is: admin123
-- Password for jordan.reyes@example.com is: demo1234
-- (bcrypt hashes below — regenerate your own with backend/app/auth.py's
-- hash_password() if you want different demo credentials)
INSERT INTO account (email, password_hash, account_type, policyholder_id, admin_role, is_active) VALUES
    ('admin@autorisk.demo', '$2b$12$V9MKFqtQg9mArHpgP0PTvuJ5IaI2lNQsZpr2L4ZBQFt9/hJ6BG/2a', 'Admin', NULL, 'Administrator', true),
    ('jordan.reyes@example.com', '$2b$12$dW6aaH5a7B1eebYHwPurxOO1c2zoyiJQ/5TRLXxuCvFzW9FDMtrOu', 'Customer', 1, NULL, true);
