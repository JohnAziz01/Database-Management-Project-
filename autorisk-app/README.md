# AutoRisk — Car Insurance Pricing & Risk Analytics

Full stack rebuild of your static HTML mockups: **React** (Vite) frontend,
**FastAPI** backend, **PostgreSQL** database, matching `car_insurance_erd.drawio`
exactly.

This whole thing was tested end-to-end while building it (schema loads, seed
data loads, the API logs in, queries policyholders, and calculates a quote
against a real Postgres database) — so the steps below are exactly what makes
it run on your machine too.

```
autorisk/
├── db/
│   ├── schema.sql       # CREATE TABLE statements from the ERD
│   └── seed.sql         # sample data + 2 demo login accounts
├── backend/              # FastAPI + SQLAlchemy
│   └── app/
│       ├── main.py       # app entry point, registers all routers
│       ├── database.py   # DB connection/session setup
│       ├── models.py     # SQLAlchemy models (one class per table)
│       ├── schemas.py    # Pydantic request/response shapes
│       ├── pricing.py    # the quote-calculation formula
│       ├── auth.py       # password hashing + JWT
│       └── routers/      # one file per resource (policyholders, claims, ...)
└── frontend/              # React (Vite)
    └── src/
        ├── main.jsx, App.jsx
        ├── api/client.js       # all fetch() calls to the backend, in one place
        ├── context/AuthContext.jsx
        ├── components/         # Sidebar, Layout, KpiCard, StatusPill, RequireAuth
        └── pages/               # one component per page (Login, Dashboard, ...)
```

## 1. Install prerequisites (once)

You'll need **PostgreSQL**, **Python 3.10+**, and **Node.js 18+** installed
locally. If you're on the same kind of Linux setup as this project was built
on:

```bash
sudo apt install postgresql postgresql-contrib
sudo service postgresql start
```

On macOS: `brew install postgresql@16 && brew services start postgresql@16`.
On Windows: install via the official PostgreSQL installer, or use WSL2 +
the apt instructions above.

## 2. Create the database

```bash
sudo -u postgres createdb autorisk
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';"   # or your own password

psql -U postgres -d autorisk -f db/schema.sql
psql -U postgres -d autorisk -f db/seed.sql
```

Demo login accounts the seed data creates:

| Email                         | Password   | Role     |
|--------------------------------|------------|----------|
| `admin@autorisk.demo`          | `admin123` | Admin    |
| `jordan.reyes@example.com`     | `demo1234` | Customer |

## 3. Run the backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate    # optional but recommended
pip install -r requirements.txt

cp .env.example .env
# edit .env if your Postgres password/port differs from the default

uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000/docs` — that's FastAPI's auto-generated,
interactive API explorer. Try `POST /api/auth/login` there with the demo
credentials above before touching the frontend at all; it's the fastest way
to confirm the database connection works.

## 4. Run the frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`, sign in with the demo credentials. The Vite
dev server proxies any `/api/...` request straight to FastAPI on port 8000
(see `vite.config.js`), so you never hit a CORS error in development.

## What's fully wired up vs. what's practice

Fully working, frontend → backend → Postgres:
Login/JWT auth, Dashboard (live aggregate KPIs), Policyholders (search +
create), Policies, Vehicles, Claims, Coverage, Regions, and the Quote
calculator (runs the real pricing formula against a real rate table row).

Intentionally left as practice: **Rate Tables, Risk Analysis, Reports, and
Accounts**. The ERD and database tables for all of them already exist —
`ComingSoon.jsx` explains the exact 5-step recipe to wire each one up
yourself, using `Regions.jsx` + `backend/app/routers/regions.py` as the
template. That's genuinely the best way to make the React/FastAPI pattern
stick — I'd rather hand you 8 solid worked examples and have you finish the
last 4 than hand you 12 examples you never had to write yourself.

---

## A plain-language React crash course, using the files above

**Component** — a component is just a JavaScript function that returns
markup (JSX). `Login`, `Dashboard`, `KpiCard` are all components. You build
a UI by nesting components inside each other, the same way you'd nest HTML
tags — except now each "tag" can have its own logic and memory.

**JSX** — the HTML-looking syntax inside your `.jsx` files
(`<div className="card">...</div>`). It's not HTML — it compiles down to
plain `React.createElement(...)` calls. Two habits to unlearn from HTML:
use `className` instead of `class`, and every tag must close (`<input />`,
not `<input>`).

**Props** — how a parent component passes data down into a child. Look at
`components/KpiCard.jsx`: it receives `label`, `value`, `delta` as props
and just displays them. `pages/Dashboard.jsx` decides *what* values to pass
in. Props flow one direction: parent → child, never child → parent
(that's what callback props like `onCreated` in `Policyholders.jsx` are
for — the child calls a function the parent handed it).

**State (`useState`)** — a component's own memory. `const [email, setEmail]
= useState("")` in `pages/Login.jsx` gives you a value (`email`) and a
function to update it (`setEmail`). Calling the setter is what makes React
re-render that component with the new value. Everything on screen that
changes over time (a typed character, a loaded list, whether a modal is
open) lives in some `useState`.

**Controlled inputs** — connecting an `<input>`'s `value` to state and its
`onChange` to a setter, so state is always the single source of truth for
what's in the box, instead of reading it out of the DOM later. Every form
field in `Login.jsx`, `Quote.jsx`, and `Policyholders.jsx`'s add-form works
this way.

**Effects (`useEffect`)** — code that runs *after* a component renders, for
things that aren't part of rendering itself: fetching data, subscriptions,
timers. `pages/Dashboard.jsx` uses `useEffect(() => { ...fetch... }, [])`
— the `[]` means "run once, right after this component first appears".
`pages/Policyholders.jsx` uses `useEffect(..., [search, regionId])` instead
— React re-runs that effect any time `search` or `regionId` changes, which
is how the live search works without you manually wiring an event.

**Rendering lists (`.map` + `key`)** — instead of writing one `<tr>` per
row by hand, you keep your data as a plain JS array and `.map()` it into
JSX elements (see the `recentClaims.map(...)` in `Dashboard.jsx`). Every
element in a mapped list needs a unique `key` prop so React can track which
item is which across re-renders — always use a real ID (`c.claim_id`),
never the array index.

**Conditional rendering** — no special syntax needed, just JavaScript:
`{loading ? <Spinner/> : <Table/>}` or `{error && <ErrorBox/>}`. You'll see
both patterns throughout the `pages/` folder for loading/empty/error states.

**Context (`useContext`)** — a way to make some state (like "who's logged
in") available to any component in the tree without manually passing it
down through every layer as props. `context/AuthContext.jsx` sets one up;
any component calls `useAuth()` to read `user` or call `login()`/`logout()`.

**Routing (`react-router-dom`)** — `App.jsx` maps URLs to components.
`<Route path="/dashboard" element={<Dashboard />} />` means "when the URL is
/dashboard, render `<Dashboard />`". Nested routes (`Layout` wrapping every
page) mean the sidebar renders once and just swaps out the `<Outlet />`
content as you navigate — no full page reload, unlike the old
`window.location.href` approach in `login.html`.

**Talking to the backend** — `api/client.js` is the only file that calls
`fetch()`. Every page imports `{ api }` and calls something like
`api.getPolicyholders()` instead of writing raw fetch calls inline. This
keeps the "how do I talk to the server" logic in one place, and the "what
do I do with the data" logic in the page components.

### Suggested next steps, in order

1. Get the app running locally (sections 1–4 above) and click through the
   pages that already work.
2. Read `pages/Login.jsx` top to bottom with the comments — it's the
   smallest complete example of state + a form + calling the API.
3. Read `pages/Dashboard.jsx` next — same idea, plus `useEffect` for
   fetching on load.
4. Read `pages/Policyholders.jsx` — the "advanced" version: search,
   filtering, and a child form component.
5. Pick one of the 4 practice pages and build it yourself, backend route
   first, then the page. Use `regions.py` / `Regions.jsx` as your template.
