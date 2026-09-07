# Car Insurance ERD

An Entity-Relationship Diagram modeling the core data structure of a car insurance system.

## Overview

This schema represents the primary data managed by a car insurance company, including customers, vehicles, policies, coverage options, regional pricing, claims, and claim payments. It is a design and schema project centered on the ERD, with optional generated SQL DDL.

## Entities

| Entity | Purpose |
|---|---|
| `REGION` | Represents a geographic hierarchy and stores a base risk factor used for pricing. |
| `POLICYHOLDER` | Stores customer identity, license, contact, risk-tier, and regional information. |
| `VEHICLE` | Stores vehicles owned by policyholders, including VIN, make, model, year, power, and usage type. |
| `COVERAGE` | Catalogs available insurance coverage types, such as liability, collision, and comprehensive. |
| `RATE_TABLE` | Defines regional pricing rules and adjustment factors for each coverage over a date range. |
| `POLICY` | Represents an insurance contract for one policyholder and one vehicle during a defined period. |
| `POLICY_COVERAGE` | Junction entity connecting policies and coverages while storing limits, deductibles, and premiums. |
| `CLAIM` | Stores incidents reported against an insurance policy. |
| `CLAIM_PAYMENT` | Stores claim payments or installments using a composite key of `claim_id` and `payment_seq`. |
| `ACCOUNT` | Stores login information for customers and administrators. |

## Relationships

| Relationship | Cardinality | Explanation |
|---|---|---|
| `REGION` → `REGION` | One-to-many | A region may contain child regions, supporting country, state, and city hierarchies. |
| `REGION` → `POLICYHOLDER` | One-to-many | A region may be associated with multiple policyholders. |
| `REGION` → `RATE_TABLE` | One-to-many | A region may have multiple coverage-specific pricing rules. |
| `POLICYHOLDER` → `VEHICLE` | One-to-many | A policyholder may own multiple vehicles. |
| `POLICYHOLDER` → `POLICY` | One-to-many | A policyholder may hold multiple insurance policies. |
| `POLICYHOLDER` → `ACCOUNT` | Optional one-to-one (`0..1`) | A policyholder may have zero or one customer login account. |
| `VEHICLE` → `POLICY` | One-to-many | A vehicle may be insured by multiple policies over time. |
| `POLICY` ↔ `COVERAGE` | Many-to-many | A policy can include multiple coverages, and a coverage can appear on many policies through `POLICY_COVERAGE`. |
| `RATE_TABLE` → `POLICY_COVERAGE` | Logical pricing lookup | Rate rules are consulted when a policy is created; there is intentionally no foreign key between these entities. |
| `POLICY` → `CLAIM` | One-to-many | A policy may have multiple reported claims. |
| `CLAIM` → `CLAIM_PAYMENT` | One-to-many | A claim may have one or more payments or installments. `CLAIM_PAYMENT` is a weak entity identified by `claim_id` and `payment_seq`. |
| `ACCOUNT` → administrator role | Exclusive subtype pattern | An account represents either a customer linked to a `POLICYHOLDER` or an administrator identified by `admin_role`. |

## Design Notes

- **Self-referencing region hierarchy:** `REGION` uses `parent_region_id` to model geographic levels such as country, state, and city. Each region can have a parent region and multiple child regions.
- **Historical pricing preservation:** `RATE_TABLE` is connected to `POLICY_COVERAGE` only through a logical business-logic lookup at policy-creation time. There is **no foreign key** between them. This allows a policy to retain its historical premium, limit, and deductible values even when pricing rules change later.
- **Weak claim payment entity:** `CLAIM_PAYMENT` depends on `CLAIM` for identification and uses the composite key `(claim_id, payment_seq)` to distinguish multiple payments for the same claim.
- **Exclusive account subtypes:** `ACCOUNT` supports both customer and administrator logins. A customer account references `POLICYHOLDER` and an administrator account uses `admin_role` instead. Mutually exclusive `CHECK` constraints enforce that an account cannot represent both types.
- **Policy coverage details:** Coverage-specific values are stored on `POLICY_COVERAGE` because limits, deductibles, and premiums may differ between policies using the same coverage type.

## Viewing and Editing the Diagram

The ERD is stored in `car_insurance_erd.drawio`.

To view or edit it:

1. Open the file at [diagrams.net](https://app.diagrams.net/).
2. Choose **Open Existing Diagram** and select `car_insurance_erd.drawio`.
3. Alternatively, install the **Draw.io Integration** extension in VS Code and open the file directly.

## Tech/Tools

- **Diagramming:** draw.io (diagrams.net)
- **File format:** `.drawio`
- **Optional output:** Generated SQL DDL for database implementation