# Car Insurance Management System

A database-backed design for managing customers, vehicles, insurance policies, coverage, pricing, claims, and payments.

## Overview

The Car Insurance Management System supports the core operations of a car insurance company from customer onboarding through policy management and claim settlement. Customers can maintain their personal and vehicle information, review their policies and coverage, and track reported claims. Administrators can manage coverage catalogs, configure regional pricing rules, review policy data, and process claim payments.

This repository currently contains the system's database design and Entity-Relationship Diagram (ERD), with optional generated SQL DDL for implementation.

## Application Scope

### Customer Operations

- Create and maintain a customer profile, including identity, license, contact, and risk information.
- Associate one or more vehicles with a policyholder account.
- View active and historical insurance policies.
- Review the coverage, limits, deductibles, and premiums attached to each policy.
- Report incidents against an existing policy.
- Track claim details and claim payment installments.

### Administrator Operations

- Maintain the coverage catalog, including liability, collision, and comprehensive coverage.
- Organize regions into a country, state, and city hierarchy.
- Configure regional risk factors and coverage-specific rate rules.
- Create policies for eligible policyholders and vehicles.
- Review claims and record one or more payments for each claim.
- Manage administrator accounts separately from customer accounts.

### Policy and Pricing Workflow

1. A policyholder is registered and assigned to a region.
2. The policyholder adds one or more vehicles.
3. Available coverages are selected for a vehicle and policy period.
4. The applicable regional rate rules are consulted when the policy is created.
5. The selected limits, deductibles, and calculated premiums are stored on the policy.
6. Claims and payments are recorded against the policy throughout its lifetime.

## Core Data Model

| Entity | Application responsibility |
|---|---|
| `REGION` | Maintains geographic hierarchy and the base risk factor used for pricing. |
| `POLICYHOLDER` | Stores customer identity, license, contact, risk tier, and region. |
| `VEHICLE` | Stores vehicles owned by policyholders, including VIN, make, model, year, power, and usage type. |
| `COVERAGE` | Defines the available insurance coverage types. |
| `RATE_TABLE` | Stores regional pricing rules and adjustment factors by coverage and date range. |
| `POLICY` | Represents an insurance contract for one policyholder and one vehicle. |
| `POLICY_COVERAGE` | Connects policies to coverages and stores policy-specific limits, deductibles, and premiums. |
| `CLAIM` | Records incidents reported against a policy. |
| `CLAIM_PAYMENT` | Records payments or installments made for a claim. |
| `ACCOUNT` | Provides login records for customers and administrators. |

## Key Relationships

- A `REGION` can contain child regions through `parent_region_id`, supporting country, state, and city levels.
- A region can be associated with many policyholders and many rate-table entries.
- A policyholder can own multiple vehicles and hold multiple policies.
- A vehicle can be covered by multiple policies over time.
- A policy can include multiple coverages, and a coverage can be used by multiple policies through `POLICY_COVERAGE`.
- A policy can have multiple claims, and each claim can have multiple payments.
- A policyholder may have zero or one customer account.

## Business Rules and Design Decisions

- **Historical pricing:** `RATE_TABLE` is used as a logical business-logic lookup when a policy is created. It has no foreign key to `POLICY_COVERAGE`; this preserves the policy's stored premium, limit, and deductible values when rates change later.
- **Regional hierarchy:** `REGION` is self-referencing so the application can represent geographic levels without separate country, state, and city tables.
- **Weak claim payments:** `CLAIM_PAYMENT` depends on `CLAIM` and uses the composite key `(claim_id, payment_seq)` to identify each payment or installment.
- **Exclusive account types:** An `ACCOUNT` represents either a customer or an administrator. Customer accounts reference `POLICYHOLDER`, while administrator accounts use `admin_role`. Mutually exclusive `CHECK` constraints prevent an account from being both.
- **Policy-specific coverage values:** Limits, deductibles, and premiums belong to `POLICY_COVERAGE` because the same coverage type can have different terms on different policies.

## Project Files

- `car_insurance_erd.drawio` — editable Entity-Relationship Diagram for the system.
- `README.md` — system overview, workflows, and database design decisions.
- Generated SQL DDL may be added to implement the schema in a relational database.

## Viewing and Editing the ERD

Open `car_insurance_erd.drawio` with either of these tools:

1. [diagrams.net](https://app.diagrams.net/) — choose **Open Existing Diagram** and select the file.
2. The **Draw.io Integration** extension for VS Code — open the file directly in the editor.

## Tech/Tools

- **Diagramming:** draw.io (diagrams.net)
- **Data modeling:** Entity-Relationship Diagram and relational schema design
- **Potential implementation output:** SQL DDL

## Project Status

The current deliverable is the database design for the Car Insurance Management System. Application code, database migrations, and a user interface can be built from this schema in a future implementation phase.