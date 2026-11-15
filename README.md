# Car Insurance Management System

A database-backed design for managing customers, vehicles, insurance policies, coverage, pricing, claims, and payments.

## Overview

The Car Insurance Management System supports the core operations of a car insurance company from customer onboarding through policy management and claim settlement. Customers can maintain their personal and vehicle information, review their policies and coverage, and track reported claims. Administrators can manage coverage catalogs, configure regional pricing rules, review policy data, and process claim payments.

This repository contains the system's database design and Entity-Relationship Diagram (ERD), plus **AutoRisk**, a working full-stack implementation: a PostgreSQL database, a FastAPI (Python) backend and a React (Vite) frontend.

**To run the project, jump to [How to Run the Project (Step by Step)](#how-to-run-the-project-step-by-step).**

GitHub repository: https://github.com/JohnAziz01/Database-Management-Project-

## Project Overview

### Purpose and Scope

The Car Insurance Management System is designed to support the operational workflow of a modern insurance provider, spanning customer onboarding, policy lifecycle management, pricing, claims handling, and payment tracking. The system centralizes policyholder, vehicle, coverage, and financial data to improve administrative efficiency, enforce business rules, and maintain an auditable record of insurance transactions.

The scope of the project includes both customer-facing and administrative capabilities. Customers can register profiles, add vehicles, review policy information, and report incidents. Administrators can maintain reference data such as coverage types and regional pricing tables, manage policy records, and process claim settlements. The design is intended to represent a realistic insurance platform, with emphasis on data integrity, policy-specific coverage values, and geographic pricing logic.

### Main Features

- Policyholder and vehicle management for customer accounts and insurance portfolios.
- Coverage catalog management with policy-specific limits, deductibles, and premiums.
- Regional pricing rules based on geographic hierarchy and risk factors.
- Policy creation workflow that stores contractual terms at the time of issuance.
- Claims submission and payment tracking across multiple claim installments.
- Separate account handling for customer and administrator roles with access control logic.

### Database Schema

The database model is organized around the core insurance entities and the relationships needed to preserve contractual and historical data. The schema includes policyholders, vehicles, regions, policies, coverages, pricing tables, claims, payment records, and account credentials. These tables are normalized so that the system can track both transactional information and the master configuration data required for premium calculation and reporting.

The key design principle is that pricing information is stored at the rate-table level while policy-specific values are preserved on the policy coverage record. This prevents later pricing changes from distorting the terms of an existing policy. In addition, the region hierarchy is represented using a self-referencing table, enabling country, state, and city level structures without redundant tables.

```mermaid
ERDiagram
    REGION ||--o{ POLICYHOLDER : has
    REGION ||--o{ RATE_TABLE : defines
    POLICYHOLDER ||--o{ VEHICLE : owns
    POLICYHOLDER ||--o{ POLICY : holds
    VEHICLE ||--o{ POLICY : covers
    POLICY ||--o{ POLICY_COVERAGE : includes
    COVERAGE ||--o{ POLICY_COVERAGE : applies_to
    POLICY ||--o{ CLAIM : has
    CLAIM ||--o{ CLAIM_PAYMENT : settles
    POLICYHOLDER ||--o| ACCOUNT : logs_in
    ACCOUNT }o--|| POLICYHOLDER : customer
```

Figure 1. Database schema overview.

### System Architecture

The system architecture follows a layered design that separates user interaction, business logic, and persistent data storage. A web application provides the user interface for both customers and administrators. Requests are routed through an application layer that validates inputs, enforces business rules, and coordinates database operations. The database stores the authoritative insurance data and supports relational queries for policy, claim, and pricing information.

The major components include the frontend interface, backend application services, authentication and authorization logic, and the relational database. These components interact through structured API requests, where the application layer reads and writes data based on business rules such as policy eligibility, premium calculation, and claim validation.

```mermaid
flowchart LR
    A[Customer / Administrator] --> B[Web Frontend]
    B --> C[Application API]
    C --> D[Authentication & Authorization]
    C --> E[Policy / Coverage / Claim Services]
    E --> F[(Relational Database)]
    F --> G[Regions]
    F --> H[Policyholders]
    F --> I[Vehicles]
    F --> J[Policies]
    F --> K[Claims and Payments]
    F --> L[Rate Tables]
```

Figure 2. System architecture diagram.

### System Workflow

1. A policyholder registers an account and is associated with a region.
2. The policyholder adds one or more vehicles to the system.
3. The administrator or application selects eligible coverages and a valid policy period.
4. Regional pricing rules are checked to calculate the applicable premium values.
5. A policy is created with coverage-specific limits, deductibles, and stored premium amounts.
6. During the lifetime of the policy, claims are reported and linked to the relevant policy.
7. Claim payments are recorded as installments or settlements, creating an auditable payment history.

This workflow ensures that each contract reflects the pricing conditions in effect at issuance while preserving the historical record of claims and payments. The resulting structure supports both operational use and future reporting, analytics, and policy review functions.

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

```
Database-Management-Project/
├── README.md                    # this file: design overview + how to run
├── Project_Report.docx          # written project report
├── car_insurance_erd.drawio     # editable ERD (open with diagrams.net)
└── autorisk-app/                # the working application
    ├── db/
    │   ├── schema.sql           # CREATE TABLE statements generated from the ERD
    │   └── seed.sql             # sample data + 2 demo login accounts
    ├── backend/                 # FastAPI + SQLAlchemy (Python)
    │   ├── requirements.txt     # Python dependencies
    │   ├── .env.example         # template for the backend settings file
    │   └── app/
    │       ├── main.py          # API entry point, registers all routers
    │       ├── database.py      # database connection / session setup
    │       ├── models.py        # one SQLAlchemy class per table
    │       ├── schemas.py       # Pydantic request/response shapes
    │       ├── pricing.py       # premium (quote) calculation formula
    │       ├── auth.py          # password hashing + JWT tokens
    │       └── routers/         # one file per resource (policyholders, claims, ...)
    └── frontend/                # React + Vite
        ├── package.json         # JavaScript dependencies and scripts
        ├── vite.config.js       # dev server; forwards /api/* to the backend
        └── src/
            ├── App.jsx          # page routes
            ├── api/client.js    # every call to the backend lives here
            ├── components/      # Sidebar, Layout, KpiCard, StatusPill, ...
            └── pages/           # Login, Dashboard, Policyholders, Quote, ...
```

## How to Run the Project (Step by Step)

The application has three parts, and they must be started in this order:

1. **PostgreSQL database**: stores all the data.
2. **Backend API (FastAPI)**: runs on `http://localhost:8000`.
3. **Frontend website (React)**: runs on `http://localhost:5173` and is what you open in the browser.

Each step below gives commands for **Windows (PowerShell)** and **macOS / Linux (Terminal)**.

> **Windows tip:** extract the project to a short path such as `C:\AutoRisk`. Very long or deeply nested folder paths can make `pip install` fail because of the Windows path-length limit.

### Step 0: Install the prerequisites (one time only)

| Software | Version | Download | Check it worked |
|---|---|---|---|
| PostgreSQL | 14 or newer | https://www.postgresql.org/download/ | `psql --version` |
| Python | 3.10 or newer | https://www.python.org/downloads/ | `python --version` |
| Node.js (includes npm) | 18 or newer | https://nodejs.org/ | `node -v` and `npm -v` |

Notes:

- **Windows (PostgreSQL):** the installer asks you to choose a password for the `postgres` user. **Write it down**, because you need it in Steps 1 and 2. Keep the default port, `5432`.
- **Windows (Python):** tick **"Add python.exe to PATH"** in the installer.
- **Windows (`psql` not found):** if `psql` is not recognised, add PostgreSQL's `bin` folder to the PATH for the current window (change `17` to your installed version):
  ```powershell
  $env:Path += ";C:\Program Files\PostgreSQL\17\bin"
  ```
- **macOS:** `brew install postgresql@16 python node`, then `brew services start postgresql@16`.
- **Ubuntu / Debian:** `sudo apt install postgresql postgresql-contrib python3 python3-venv nodejs npm`, then `sudo service postgresql start`.

### Step 1: Create the database and load the data

Open a terminal **in the `autorisk-app` folder**:

```powershell
cd path\to\Database-Management-Project\autorisk-app
```

**1a. Create an empty database called `autorisk`.** Enter your `postgres` password when asked.

Windows (PowerShell) / macOS:
```powershell
createdb -U postgres -h localhost autorisk
```
Linux (the default `postgres` user has no password):
```bash
sudo -u postgres createdb autorisk
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';"
```

**1b. Create the tables** (region, policyholder, vehicle, coverage, policy, policy_coverage, rate_table, claim, claim_payment, account):
```bash
psql -U postgres -h localhost -d autorisk -f db/schema.sql
```
The first time you run this, PostgreSQL prints notices such as `table "claim_payment" does not exist, skipping`. These are normal: the script drops old tables before creating new ones, so it is safe to re-run.

**1c. Load the sample data:**
```bash
psql -U postgres -h localhost -d autorisk -f db/seed.sql
```

**1d. Check it worked:**
```bash
psql -U postgres -h localhost -d autorisk -c "SELECT first_name, last_name FROM policyholder;"
```
You should see 3 policyholders (for example, Jordan Reyes).

The seed data also creates these **demo login accounts**:

| Email | Password | Role |
|---|---|---|
| `admin@autorisk.demo` | `admin123` | Administrator |
| `jordan.reyes@example.com` | `demo1234` | Customer |

### Step 2: Start the backend API

Open a **new terminal** and go to the backend folder:

```bash
cd path/to/Database-Management-Project/autorisk-app/backend
```

**2a. Create a Python virtual environment** (an isolated folder for this project's packages) and activate it:

Windows (PowerShell):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```
> If PowerShell says *"running scripts is disabled on this system"*, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`, then run the activate command again.
> In Command Prompt (cmd), activate with `.venv\Scripts\activate.bat` instead.

macOS / Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
```
Once it is active, your prompt starts with `(.venv)`.

**2b. Install the Python packages:**
```bash
pip install -r requirements.txt
```

**2c. Create the settings file (`.env`)** by copying the template:

Windows: `copy .env.example .env`  macOS / Linux: `cp .env.example .env`

Open `.env` in a text editor and replace `yourpassword` with **your** PostgreSQL password from Step 0:
```ini
DATABASE_URL=postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/autorisk
JWT_SECRET=change-this-to-a-long-random-string
CORS_ORIGIN=http://localhost:5173
```
- `DATABASE_URL` tells the backend where the database is, in the form `user:password@host:port/database`.
- `JWT_SECRET` signs login tokens. Any long random string works.
- `CORS_ORIGIN` is the address of the frontend.

**2d. Start the API server:**
```bash
uvicorn app.main:app --reload --port 8000
```
It is working when you see `Uvicorn running on http://127.0.0.1:8000`. **Leave this terminal open.**

**2e. Test the API (optional, recommended):**
- Open http://localhost:8000/api/health. It should show `{"status":"ok"}`.
- Open http://localhost:8000/docs to see the interactive API documentation. Expand `POST /api/auth/login`, click **Try it out**, enter
  `{"email": "admin@autorisk.demo", "password": "admin123"}` and click **Execute**. A response that contains an `access_token` confirms the backend can read the database.

### Step 3: Start the frontend website

Open a **third terminal** and go to the frontend folder:

```bash
cd path/to/Database-Management-Project/autorisk-app/frontend
```

**3a. Install the JavaScript packages** (needed only the first time):
```bash
npm install
```

**3b. Start the development server:**
```bash
npm run dev
```
It is working when you see `Local: http://localhost:5173/`. **Leave this terminal open as well.**

### Step 4: Use the application

1. Open **http://localhost:5173** in your browser.
2. Log in with `admin@autorisk.demo` / `admin123`.
3. Explore the pages:
   - **Dashboard**: live KPIs (policy counts, premiums, open claims) and recent claims.
   - **Policyholders**: search, filter by region, and add a new policyholder.
   - **Vehicles, Policies, Claims, Coverage, Regions**: data read directly from PostgreSQL.
   - **Quote**: calculates a premium using the regional rate table and the pricing formula.

The frontend sends every `/api/...` request to the backend on port 8000 (configured in `vite.config.js`), so both servers from Steps 2 and 3 must be running.

**Status of the remaining pages:** Rate Tables, Risk Analysis, Reports and Accounts already have their database tables. Their pages show a "Coming Soon" placeholder.

### Step 5: Stop the application

Press `Ctrl + C` in the backend terminal and in the frontend terminal. To start the application again later, you don't need to repeat the installation. Just run:

```bash
# Terminal 1 (backend)
cd autorisk-app/backend
.\.venv\Scripts\Activate.ps1         # Windows   (macOS/Linux: source .venv/bin/activate)
uvicorn app.main:app --reload --port 8000

# Terminal 2 (frontend)
cd autorisk-app/frontend
npm run dev
```

To reset the database to the original sample data, re-run Steps 1b and 1c.

### Optional: Use a cloud database (Neon) instead of a local PostgreSQL

1. Create a free project at https://neon.tech and copy its connection string.
2. Load the tables and data (run in `autorisk-app`):
   ```bash
   psql "postgresql://USER:PASSWORD@HOST/neondb?sslmode=require" -f db/schema.sql
   psql "postgresql://USER:PASSWORD@HOST/neondb?sslmode=require" -f db/seed.sql
   ```
3. In `backend/.env`, set the same connection string, starting with `postgresql+psycopg2://`:
   ```ini
   DATABASE_URL=postgresql+psycopg2://USER:PASSWORD@HOST/neondb?sslmode=require
   ```
4. Continue from Step 2d.

### Troubleshooting

| Problem | Fix |
|---|---|
| `psql` / `createdb` is not recognised | Add PostgreSQL's `bin` folder to PATH (see Step 0). |
| `password authentication failed for user "postgres"` | The password in the command or in `backend/.env` is wrong. Use the one you chose when you installed PostgreSQL. |
| `database "autorisk" does not exist` | Step 1a was skipped. Run `createdb` again. |
| `connection refused` on port 5432 | The PostgreSQL service is not running. On Windows, start it in *Services* (`postgresql-x64-XX`). |
| `ModuleNotFoundError` when you start uvicorn | The virtual environment is not active. Activate it (Step 2a) and run `pip install -r requirements.txt`. |
| `pip install` fails with a long-path error on Windows | Move the project to a short path such as `C:\AutoRisk`. |
| The login page says "Failed to fetch" or shows a network error | The backend is not running. Start it (Step 2d) and check http://localhost:8000/api/health. |
| `Port 8000` or `5173` is already in use | Close the other program using it, or start uvicorn with `--port 8001` and change the `target` in `frontend/vite.config.js` to match. |
| `npm` is not recognised | Install Node.js (Step 0), then open a new terminal. |

## Viewing and Editing the ERD

Open `car_insurance_erd.drawio` with either of these tools:

1. [diagrams.net](https://app.diagrams.net/): choose **Open Existing Diagram** and select the file.
2. The **Draw.io Integration** extension for VS Code: open the file directly in the editor.

## Tech/Tools

- **Database:** PostgreSQL (`db/schema.sql`, `db/seed.sql`)
- **Backend:** Python, FastAPI, SQLAlchemy, Pydantic, JWT authentication (python-jose, passlib/bcrypt)
- **Frontend:** React 18, React Router, Vite
- **Diagramming:** draw.io (diagrams.net)
- **Data modeling:** Entity-Relationship Diagram and relational schema design

## Project Status

- Database design (ERD) and PostgreSQL schema: complete.
- Full-stack application: login, dashboard, policyholders, vehicles, policies, claims, coverage, regions and quote calculator all work end to end (React → FastAPI → PostgreSQL).
- Rate Tables, Risk Analysis, Reports and Accounts pages: the database tables exist, and the pages show a "Coming Soon" placeholder.
