/**
 * PRACTICE PAGE: Rate Tables, Reports, Risk Analysis, and Accounts don't
 * have backend endpoints wired up yet — this is intentional. Follow the
 * exact same recipe used for Regions.jsx / Coverage.jsx to build these
 * out yourself once you're comfortable:
 *
 *   1. Backend: add a SQLAlchemy model field selection + a Pydantic
 *      *Out schema in backend/app/schemas.py (if new fields are needed).
 *   2. Backend: add a GET route in backend/app/routers/<name>.py that
 *      queries the table with SQLAlchemy, and register it in main.py.
 *   3. Frontend: add a function to src/api/client.js that calls it.
 *   4. Frontend: copy Regions.jsx, rename it, swap the fetch call and
 *      the <table> columns for this resource's fields.
 *   5. Wire the route into App.jsx and the Sidebar's NAV_ITEMS already
 *      point at it, so it'll just start working.
 *
 * This one component is reused for all four remaining pages so the app
 * is fully navigable today — swap it out page by page as you build.
 */
export default function ComingSoon({ title }) {
  return (
    <div className="card card-pad">
      <div className="empty-state">
        <div className="empty-title">{title} — build this one yourself next</div>
        <div className="empty-sub">
          The backend model already exists in the ERD. Follow the pattern in
          Regions.jsx / backend/app/routers/regions.py to wire it up.
        </div>
      </div>
    </div>
  );
}
