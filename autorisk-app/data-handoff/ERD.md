# AutoRisk import ERD

This diagram replaces the data team's export ERD. It follows the relationships in the team snapshot's `autorisk-app/db/schema.sql`.

```mermaid
erDiagram
    REGION o|--o{ REGION : parent
    REGION o|--o{ POLICYHOLDER : residence
    REGION ||--o{ RATE_TABLE : rates
    COVERAGE ||--o{ RATE_TABLE : rates
    POLICYHOLDER ||--o{ VEHICLE : owns
    POLICYHOLDER ||--o{ POLICY : holds
    VEHICLE ||--o{ POLICY : covers
    POLICY ||--o{ POLICY_COVERAGE : includes
    COVERAGE ||--o{ POLICY_COVERAGE : selected
    POLICY ||--o{ CLAIM : has
    CLAIM ||--o{ CLAIM_PAYMENT : pays
    POLICYHOLDER o|--o{ ACCOUNT : customer

    REGION {
        int region_id PK
        int parent_region_id FK
    }
    POLICYHOLDER {
        int policyholder_id PK
        int region_id FK
    }
    VEHICLE {
        int vehicle_id PK
        int policyholder_id FK
    }
    POLICY {
        int policy_id PK
        int policyholder_id FK
        int vehicle_id FK
    }
    COVERAGE {
        int coverage_id PK
    }
    POLICY_COVERAGE {
        int policy_id PK,FK
        int coverage_id PK,FK
    }
    RATE_TABLE {
        int rate_table_id PK
        int region_id FK
        int coverage_id FK
    }
    CLAIM {
        int claim_id PK
        int policy_id FK
    }
    CLAIM_PAYMENT {
        int claim_id PK,FK
        int payment_seq PK
    }
    ACCOUNT {
        int account_id PK
        int policyholder_id FK
    }
```

The loader uses the seeded Liability coverage and leaves team accounts in place. All imported policies have one holder, vehicle, and Liability coverage row. The export uses a negative source ID for each holder, vehicle, and policy, with the positive ID retained in the analytics CSV.
