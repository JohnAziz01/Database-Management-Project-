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
- **Versioned rates:** a rate is never edited in place. Publishing a new rate version sets the old row's `expiry_date` to the new version's `effective_date`, so the full price history is kept.
- **Pricing formula:** premium = base rate × age factor × experience factor × vehicle-power factor × region factor × bonus-malus, for a **6-month term** (rate tables hold annual rates, multiplied by 6/12). Bonus-malus is the claims-history multiplier: 1.00 is neutral, below 1.00 is a no-claims discount, above 1.00 a surcharge.
- **Full Coverage:** all four coverages priced with their own rate tables, summed, then 10% off. It is offered only in regions where all four coverages have current rates.

## Project Files

```
Database-Management-Project/
├── README.md                       # this file: design overview + how to run
├── Project_Report.docx             # written project report
├── AutoRisk_Backend_DeepDive.pptx  # presentation slides
├── car_insurance_erd.drawio        # editable ERD (open with diagrams.net)
└── autorisk-app/                   # the working application
    ├── run.ps1 / run.bat           # one-command launcher for Windows (setup, start, reset-db)
    ├── db/
    │   ├── schema.sql              # CREATE TABLE statements generated from the ERD
    │   ├── seed.sql                # sample data + 2 demo login accounts
    │   └── reset_db.py             # wipes the database and reloads schema + seed
    ├── backend/                    # FastAPI + SQLAlchemy (Python)
    │   ├── requirements.txt        # Python dependencies
    │   ├── .env.example            # template for the backend settings file
    │   └── app/
    │       ├── main.py             # API entry point, registers all routers
    │       ├── database.py         # database connection / session setup
    │       ├── models.py           # one SQLAlchemy class per table
    │       ├── schemas.py          # Pydantic request/response shapes + validation rules
    │       ├── pricing.py          # premium formula, 6-month term, Full Coverage bundle
    │       ├── auth.py             # password hashing, JWT tokens, roles, login throttling
    │       ├── clock.py            # one UTC "today" shared with the database
    │       └── routers/            # one file per feature:
    │           ├── policyholders.py, vehicles.py, policies.py, claims.py,
    │           ├── coverages.py, regions.py, quote.py, dashboard.py, auth.py
    │           ├── rate_tables.py  # versioned pricing (publish a new rate version)
    │           ├── risk.py         # claim experience by rating factor
    │           ├── reports.py      # 5 business reports, preview + CSV download
    │           └── accounts.py     # staff/customer logins, enable/disable, password reset
    ├── frontend/                   # React + Vite
    │   ├── package.json            # JavaScript dependencies and scripts
    │   ├── vite.config.js          # dev server; forwards /api/* to the backend
    │   └── src/
    │       ├── App.jsx             # page routes
    │       ├── api/client.js       # every call to the backend lives here
    │       ├── components/         # Sidebar, Layout, KpiCard, PortfolioPanels, ...
    │       └── pages/              # Dashboard, Quote, Policies, ..., RateTables,
    │                               # RiskAnalysis, Reports, Accounts
    ├── data-handoff/               # real-world data (freMTPL2) prepared for our schema
    │   ├── sample/                 # 200-policy sample as CSV files
    │   ├── load.sql                # transactional, re-runnable loader (needs psql)
    │   └── load_with_python.py     # the same loader without psql
    └── testing/                    # automated tests (unit, API, browser) + test docs
        ├── run_tests.ps1           # runs the test suites
        └── docs/                   # test plan, test cases, bug reports, fix report
```

## How to Run the Project (Step by Step)

The application has three parts, and they must be started in this order:

1. **PostgreSQL database**: stores all the data.
2. **Backend API (FastAPI)**: runs on `http://localhost:8000`.
3. **Frontend website (React)**: runs on `http://localhost:5173` and is what you open in the browser.

Each step below gives commands for **Windows (PowerShell)** and **macOS / Linux (Terminal)**.

> **Windows tip:** extract the project to a short path such as `C:\AutoRisk`. Very long or deeply nested folder paths can make `pip install` fail because of the Windows path-length limit.

### Quick start (Windows, one command)

If you are on Windows and already have Python, Node.js and a database (Step 0 and Step 1 below), the launcher does Steps 2 and 3 for you. In PowerShell, from the `autorisk-app` folder:

```powershell
.\run.ps1 setup      # once: creates backend\.venv, installs Python + JavaScript packages, creates backend\.env
                     # -> then open backend\.env and set DATABASE_URL (see Step 2c)
.\run.ps1            # starts the backend and frontend in two new windows and opens the browser
```

Other commands: `.\run.ps1 backend`, `.\run.ps1 frontend`, `.\run.ps1 reset-db` (wipes the database and reloads the sample data; asks you to type YES first). If PowerShell refuses to run scripts, use `run.bat` with the same arguments.

The rest of this section explains every step by hand, for Windows, macOS and Linux.

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
   - **Dashboard**: today's KPIs (active policies, premium, open claims, claims paid, policyholders), the latest claims, and a **Portfolio** section over every policy ever written: loss ratio, claims paid by policy year (hover a bar for details) and a table by region.
   - **New Quote**: prices a driver for a **6-month term** from the regional rate tables. Pick one coverage, or **Full Coverage** (all four coverages together, 10% bundle discount) to see an itemized breakdown.
   - **Policies, Policyholders, Vehicles, Claims, Coverage, Regions**: data read live from PostgreSQL. Policyholders can be searched, filtered by region and added.
   - **Rate Tables**: every price version per region and coverage (Current, Scheduled, Expired). **Revise** publishes a new version from a chosen date; the old one expires that day, and policies already sold keep their price.
   - **Risk Analysis**: claim frequency, average claim cost and loss ratio by driver age, experience, vehicle power, vehicle age, bonus-malus, region and risk tier.
   - **Reports**: claims register, payments ledger, policy register, premium & claims by region, and coverage mix, each with a date filter, a preview and **Download CSV**.
   - **Accounts**: every login with its role and last sign-in; add staff or customer accounts, enable/disable them, reset passwords.
4. Log out and log in as the customer `jordan.reyes@example.com` / `demo1234` to see the customer view: only their own records, and no access to the admin pages.

**Staff roles:** an `Analyst` can view every admin page but cannot change rates or accounts. `Administrator` and `Manager` can. The demo admin is an `Administrator`. You can create an Analyst on the Accounts page to try it.

The frontend sends every `/api/...` request to the backend on port 8000 (configured in `vite.config.js`), so both servers from Steps 2 and 3 must be running.

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

To reset the database to the original sample data, re-run Steps 1b and 1c (on Windows: `.\run.ps1 reset-db`).

### Step 6 (optional): Load real insurance data

`autorisk-app/data-handoff/` contains a 200-policy sample of **freMTPL2**, a public French motor-insurance dataset, already cleaned and mapped to our schema (see `data-handoff/README.md` for how it was cleaned). It adds 22 French regions, 200 historical policies with their drivers and vehicles, 111 paid claims, and Liability rates for every region. Imported rows use negative IDs, so they never clash with the app's own rows, and the app shows them with an "H" (for example `POL-H0001`).

Load it **after** Step 1 (schema + seed). Either:

```bash
# with psql: run from the sample folder, because load.sql reads the CSV files next to it
cd autorisk-app/data-handoff/sample
psql -U postgres -h localhost -d autorisk -f ../load.sql
```

or, without psql, with the backend's Python (it uses `DATABASE_URL` from `backend/.env`):

```powershell
cd autorisk-app
backend\.venv\Scripts\python.exe data-handoff\load_with_python.py data-handoff\sample     # Windows
backend/.venv/bin/python data-handoff/load_with_python.py data-handoff/sample             # macOS / Linux
```

The load runs in one transaction (all rows or none) and is safe to run twice: the second run changes nothing. Afterwards the Dashboard's Portfolio section, Risk Analysis and Reports include the historical data.

### Step 7 (optional): Run the automated tests

The project has about 300 automated tests: unit tests for the pricing formula, API tests for every endpoint, and browser tests (Playwright) for the main pages. API and browser tests use their **own throwaway PostgreSQL in Docker**, never your real database. Details are in `autorisk-app/testing/README.md`.

Windows (from `autorisk-app`):
```powershell
.\testing\run_tests.ps1 setup     # once: installs pytest, Playwright and Chromium
.\testing\run_tests.ps1 unit      # pricing unit tests only: no Docker needed, under 1 second
# start Docker Desktop, then:
.\testing\run_tests.ps1           # everything; HTML report in testing\reports\report.html
```

macOS / Linux (unit tests, from `autorisk-app` with the backend virtual environment active):
```bash
pip install -r testing/requirements-test.txt
cd testing && python -m pytest unit
```

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
| A login says "value is not a valid email address" | Type the full email address, for example `admin@autorisk.demo`, not just `admin`. |
| Full Coverage is missing from the Coverage dropdown | That region does not have current rates for all four coverages. The seed data has them for Region A, B and C; check the Rate Tables page. |
| `.\testing\run_tests.ps1` cannot start the test database | Start Docker Desktop and wait until it says it is running, then try again. Unit tests (`run_tests.ps1 unit`) do not need Docker. |

## Viewing and Editing the ERD

Open `car_insurance_erd.drawio` with either of these tools:

1. [diagrams.net](https://app.diagrams.net/): choose **Open Existing Diagram** and select the file.
2. The **Draw.io Integration** extension for VS Code: open the file directly in the editor.

## Tech/Tools

- **Database:** PostgreSQL, local or hosted on Neon (`db/schema.sql`, `db/seed.sql`)
- **Backend:** Python, FastAPI, SQLAlchemy, Pydantic, Uvicorn, JWT authentication (python-jose, passlib/bcrypt)
- **Frontend:** React 18, React Router, Vite
- **Data preparation:** pandas, SQLite (pre-validation), PostgreSQL `COPY`
- **Testing:** pytest, FastAPI TestClient, Playwright (Chromium), Docker
- **Diagramming:** draw.io (diagrams.net)
- **Data modeling:** Entity-Relationship Diagram and relational schema design

## Project Status

- Database design (ERD) and PostgreSQL schema: complete.
- Full-stack application: every page works end to end (React → FastAPI → PostgreSQL): login, dashboard with portfolio analytics, quotes (single coverage or Full Coverage, 6-month term), policyholders, vehicles, policies, claims, coverage, regions, rate tables, risk analysis, reports and accounts.
- Security: every data endpoint requires a login; customers only see their own records; staff roles (Analyst read-only, Administrator/Manager full access); login throttling.
- Real-world data: a cleaned 200-policy sample of the freMTPL2 dataset can be loaded (Step 6).
- Testing: about 300 automated tests (unit, API, browser), all passing. 23 bugs found during testing are documented and fixed (`autorisk-app/testing/docs/`).
